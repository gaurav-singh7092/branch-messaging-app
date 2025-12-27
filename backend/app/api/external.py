from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ..database import get_db
from ..models import Customer, Conversation, Message, MessagePriority, MessageStatus
from ..schemas import MessageSend
from ..services import detect_priority, manager

router = APIRouter(prefix="/external", tags=["external"])


@router.post("/messages")
async def receive_external_message(
    message: MessageSend,
    db: AsyncSession = Depends(get_db)
):
    """
    External API endpoint to receive customer messages.
    This simulates messages coming from external channels (SMS, app, etc.)
    
    Can be used with Postman or any HTTP client to send messages.
    """
    # Find or create customer
    customer = None
    
    if message.customer_id:
        result = await db.execute(
            select(Customer).where(Customer.id == message.customer_id)
        )
        customer = result.scalar_one_or_none()
    
    if not customer and message.customer_email:
        result = await db.execute(
            select(Customer).where(Customer.email == message.customer_email)
        )
        customer = result.scalar_one_or_none()
    
    if not customer:
        # Create new customer
        if not message.customer_email:
            raise HTTPException(
                status_code=400,
                detail="Either customer_id or customer_email is required"
            )
        
        customer = Customer(
            name=message.customer_name or "Unknown Customer",
            email=message.customer_email,
            account_status="active"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    
    # Detect message priority
    priority, confidence = detect_priority(message.content)
    
    # Find open conversation or create new one
    conv_query = select(Conversation).where(
        Conversation.customer_id == customer.id,
        Conversation.status.in_([MessageStatus.OPEN, MessageStatus.IN_PROGRESS])
    ).order_by(Conversation.updated_at.desc())
    
    result = await db.execute(conv_query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            customer_id=customer.id,
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
        # Update priority if new message is more urgent
        priority_order = {
            MessagePriority.LOW: 0,
            MessagePriority.MEDIUM: 1,
            MessagePriority.HIGH: 2,
            MessagePriority.URGENT: 3
        }
        if priority_order.get(priority, 0) > priority_order.get(conversation.priority, 0):
            conversation.priority = priority
    
    # Create the message
    db_message = Message(
        conversation_id=conversation.id,
        customer_id=customer.id,
        content=message.content,
        is_from_customer=True,
        priority=priority
    )
    db.add(db_message)
    
    # Update timestamps
    conversation.updated_at = datetime.utcnow()
    customer.last_activity = datetime.utcnow()
    
    await db.commit()
    await db.refresh(db_message)
    
    # Broadcast new message to all connected agents
    await manager.broadcast_new_message({
        "id": db_message.id,
        "conversation_id": conversation.id,
        "customer_id": customer.id,
        "content": message.content,
        "is_from_customer": True,
        "priority": priority.value,
        "created_at": db_message.created_at.isoformat() + "Z",
        "customer_name": customer.name,
        "customer_email": customer.email
    })
    
    return {
        "success": True,
        "message_id": db_message.id,
        "conversation_id": conversation.id,
        "customer_id": customer.id,
        "priority": priority.value,
        "priority_confidence": confidence
    }
