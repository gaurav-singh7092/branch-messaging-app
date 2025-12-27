from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, func
import os
import csv
from datetime import datetime
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./branch_messaging.db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Auto-seed if database is empty
    await seed_initial_data()


def detect_priority(message: str) -> str:
    """Simple priority detection based on keywords"""
    message_lower = message.lower()
    high_priority_keywords = ['urgent', 'emergency', 'asap', 'immediately', 'help', 'rejected', 'denied', 'problem', 'issue', 'frustrated', 'angry']
    medium_priority_keywords = ['when', 'why', 'how', 'please', 'kindly', 'waiting', 'delay', 'late']
    
    if any(kw in message_lower for kw in high_priority_keywords):
        return 'high'
    elif any(kw in message_lower for kw in medium_priority_keywords):
        return 'medium'
    return 'low'


async def seed_initial_data():
    """Seed initial data if database is empty"""
    from .models import Agent, Customer, Conversation, Message, CannedMessage, MessagePriority, MessageStatus
    
    async with async_session_maker() as session:
        # Check if agents exist
        result = await session.execute(select(func.count(Agent.id)))
        if result.scalar() > 0:
            print("Database already has data. Skipping seed.")
            return
        
        print("Seeding database with initial data...")
        
        # Create sample agents
        agents = [
            Agent(name="Alex Thompson", email="alex.t@branch.com", is_online=True),
            Agent(name="Maria Garcia", email="maria.g@branch.com", is_online=True),
            Agent(name="James Chen", email="james.c@branch.com", is_online=False),
            Agent(name="Sophie Wilson", email="sophie.w@branch.com", is_online=True),
        ]
        for agent in agents:
            session.add(agent)
        await session.flush()
        
        # Create canned messages
        canned = [
            CannedMessage(title="Greeting", content="Hello! Thank you for contacting Branch support. How can I help you today?", category="General", shortcut="/hello"),
            CannedMessage(title="Loan Status", content="I'd be happy to check the status of your loan application. Please give me a moment.", category="Loan", shortcut="/loanstatus"),
            CannedMessage(title="Closing", content="Is there anything else I can help you with today?", category="General", shortcut="/closing"),
            CannedMessage(title="Apology", content="I sincerely apologize for any inconvenience this has caused. Let me help resolve this for you.", category="General", shortcut="/sorry"),
            CannedMessage(title="Payment Info", content="You can make payments through M-Pesa. The paybill number is 123456.", category="Payment", shortcut="/pay"),
        ]
        for c in canned:
            session.add(c)
        
        # Load data from CSV file
        csv_path = Path(__file__).parent.parent / "GeneralistRails_Project_MessageData.csv"
        
        if not csv_path.exists():
            # Try alternative paths for deployment
            alt_paths = [
                Path(__file__).parent.parent.parent / "GeneralistRails_Project_MessageData.csv",
                Path("/app/GeneralistRails_Project_MessageData.csv"),
            ]
            for alt in alt_paths:
                if alt.exists():
                    csv_path = alt
                    break
        
        if not csv_path.exists():
            print(f"CSV file not found at {csv_path}, creating minimal sample data...")
            # Create minimal sample data if CSV not found
            customer = Customer(name="John Smith", email="john@email.com", phone="+1234567890", account_status="active")
            session.add(customer)
            await session.flush()
            conv = Conversation(customer_id=customer.id, agent_id=agents[0].id, status=MessageStatus.ACTIVE, priority=MessagePriority.MEDIUM, subject="General inquiry")
            session.add(conv)
            await session.flush()
            msg = Message(conversation_id=conv.id, customer_id=customer.id, content="Hello, I have a question", is_from_customer=True, priority=MessagePriority.MEDIUM)
            session.add(msg)
            await session.commit()
            print("Database seeded with minimal data!")
            return
        
        print(f"Loading messages from {csv_path}...")
        
        # Parse CSV and group messages by User ID
        user_messages = {}
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row['User ID']
                if user_id not in user_messages:
                    user_messages[user_id] = []
                user_messages[user_id].append({
                    'timestamp': row['Timestamp (UTC)'],
                    'message': row['Message Body']
                })
        
        # Sort messages by timestamp for each user
        for user_id in user_messages:
            user_messages[user_id].sort(key=lambda x: x['timestamp'])
        
        # Create customers and conversations from CSV data
        customer_map = {}  # user_id -> customer object
        agent_index = 0
        
        for user_id, messages in user_messages.items():
            # Create customer
            customer = Customer(
                name=f"Customer {user_id}",
                email=f"customer{user_id}@email.com",
                phone=f"+254{user_id.zfill(9)}",
                account_status="active",
                loan_status="pending" if any('loan' in m['message'].lower() for m in messages) else None
            )
            session.add(customer)
            await session.flush()
            customer_map[user_id] = customer
            
            # Determine conversation priority from messages
            all_text = ' '.join([m['message'] for m in messages])
            priority_str = detect_priority(all_text)
            priority = MessagePriority.HIGH if priority_str == 'high' else (MessagePriority.MEDIUM if priority_str == 'medium' else MessagePriority.LOW)
            
            # Create conversation (assign to agents round-robin)
            assigned_agent = agents[agent_index % len(agents)]
            agent_index += 1
            
            # Generate subject from first message
            first_msg = messages[0]['message'][:50] + ('...' if len(messages[0]['message']) > 50 else '')
            
            conv = Conversation(
                customer_id=customer.id,
                agent_id=assigned_agent.id,
                status=MessageStatus.ACTIVE,
                priority=priority,
                subject=first_msg
            )
            session.add(conv)
            await session.flush()
            
            # Create messages for this conversation
            for msg_data in messages:
                try:
                    timestamp = datetime.strptime(msg_data['timestamp'], '%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = datetime.utcnow()
                
                msg_priority_str = detect_priority(msg_data['message'])
                msg_priority = MessagePriority.HIGH if msg_priority_str == 'high' else (MessagePriority.MEDIUM if msg_priority_str == 'medium' else MessagePriority.LOW)
                
                message = Message(
                    conversation_id=conv.id,
                    customer_id=customer.id,
                    content=msg_data['message'],
                    is_from_customer=True,
                    priority=msg_priority,
                    created_at=timestamp
                )
                session.add(message)
        
        await session.commit()
        print(f"Database seeded successfully with {len(customer_map)} customers and their messages!")
