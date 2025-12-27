from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import Customer, Conversation, Message, MessagePriority, MessageStatus
from ..schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    MessageSend, ConversationListResponse, MessageResponse
)
from ..services import detect_priority, manager

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=List[CustomerResponse])
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all customers with optional search"""
    query = select(Customer)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Customer.name.ilike(search_term),
                Customer.email.ilike(search_term),
                Customer.phone.ilike(search_term)
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(desc(Customer.last_activity))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific customer by ID"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


@router.post("/", response_model=CustomerResponse)
async def create_customer(customer: CustomerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new customer"""
    # Check if customer with email already exists
    result = await db.execute(select(Customer).where(Customer.email == customer.email))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this email already exists")
    
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    
    return db_customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer: CustomerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a customer"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    db_customer = result.scalar_one_or_none()
    
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = customer.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_customer, field, value)
    
    db_customer.last_activity = datetime.utcnow()
    await db.commit()
    await db.refresh(db_customer)
    
    return db_customer


@router.get("/{customer_id}/conversations", response_model=List[ConversationListResponse])
async def get_customer_conversations(
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for a customer"""
    query = select(Conversation).where(
        Conversation.customer_id == customer_id
    ).options(
        selectinload(Conversation.customer),
        selectinload(Conversation.assigned_agent),
        selectinload(Conversation.messages)
    ).order_by(desc(Conversation.updated_at))
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    response = []
    for conv in conversations:
        last_message = conv.messages[-1] if conv.messages else None
        unread_count = sum(1 for m in conv.messages if m.is_from_customer and not m.read_at)
        
        response.append(ConversationListResponse(
            id=conv.id,
            customer_id=conv.customer_id,
            agent_id=conv.agent_id,
            status=conv.status,
            priority=conv.priority,
            subject=conv.subject,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            customer=conv.customer,
            assigned_agent=conv.assigned_agent,
            last_message=last_message,
            unread_count=unread_count
        ))
    
    return response


@router.post("/{customer_id}/messages", response_model=MessageResponse)
async def send_customer_message(
    customer_id: int,
    message: MessageSend,
    db: AsyncSession = Depends(get_db)
):
    """Customer sends a new message (creates conversation if needed)"""
    # Verify customer exists
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Detect message priority
    priority, confidence = detect_priority(message.content)
    
    # Find open conversation or create new one
    conv_query = select(Conversation).where(
        Conversation.customer_id == customer_id,
        Conversation.status.in_([MessageStatus.OPEN, MessageStatus.IN_PROGRESS])
    ).order_by(desc(Conversation.updated_at))
    
    result = await db.execute(conv_query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            customer_id=customer_id,
            status=MessageStatus.OPEN,
            priority=priority,
            subject=message.content[:100] if len(message.content) > 100 else message.content
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        # Broadcast new conversation
        await manager.broadcast_new_conversation({
            "id": conversation.id,
            "customer_id": conversation.customer_id,
            "priority": conversation.priority.value,
            "status": conversation.status.value,
            "subject": conversation.subject,
            "customer_name": customer.name,
            "customer_email": customer.email
        })
    else:
        # Update conversation priority if new message is more urgent
        if priority.value > conversation.priority.value:
            conversation.priority = priority
    
    # Create the message
    db_message = Message(
        conversation_id=conversation.id,
        customer_id=customer_id,
        content=message.content,
        is_from_customer=True,
        priority=priority
    )
    db.add(db_message)
    
    # Update conversation and customer timestamps
    conversation.updated_at = datetime.utcnow()
    customer.last_activity = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_message)
    
    # Broadcast new message to all agents
    await manager.broadcast_new_message({
        "id": db_message.id,
        "conversation_id": conversation.id,
        "customer_id": customer_id,
        "content": message.content,
        "is_from_customer": True,
        "priority": priority.value,
        "created_at": db_message.created_at.isoformat(),
        "customer_name": customer.name
    })
    
    return db_message
