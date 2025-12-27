from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models import Conversation, Message, Customer, Agent, MessagePriority, MessageStatus
from ..schemas import (
    ConversationResponse, ConversationListResponse, ConversationUpdate,
    AgentMessageSend, MessageResponse, MessagePriorityEnum, MessageStatusEnum
)
from ..services import manager

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=List[ConversationListResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    status: Optional[MessageStatusEnum] = None,
    priority: Optional[MessagePriorityEnum] = None,
    agent_id: Optional[int] = None,
    unassigned: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all conversations with filters.
    Results are ordered by priority (urgent first) and then by updated time.
    """
    query = select(Conversation).options(
        selectinload(Conversation.customer),
        selectinload(Conversation.assigned_agent),
        selectinload(Conversation.messages)
    )
    
    if status:
        query = query.where(Conversation.status == status)
    
    if priority:
        query = query.where(Conversation.priority == priority)
    
    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    
    if unassigned:
        query = query.where(Conversation.agent_id.is_(None))
    
    # Order by priority (URGENT > HIGH > MEDIUM > LOW) and then by update time
    query = query.order_by(
        # Priority ordering - urgent first
        desc(Conversation.priority == MessagePriority.URGENT),
        desc(Conversation.priority == MessagePriority.HIGH),
        desc(Conversation.priority == MessagePriority.MEDIUM),
        desc(Conversation.updated_at)
    ).offset(skip).limit(limit)
    
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


@router.get("/stats")
async def get_conversation_stats(db: AsyncSession = Depends(get_db)):
    """Get conversation statistics"""
    # Total conversations by status
    status_query = select(
        Conversation.status,
        func.count(Conversation.id)
    ).group_by(Conversation.status)
    
    result = await db.execute(status_query)
    status_counts = {str(row[0].value): row[1] for row in result.all()}
    
    # Total conversations by priority
    priority_query = select(
        Conversation.priority,
        func.count(Conversation.id)
    ).group_by(Conversation.priority)
    
    result = await db.execute(priority_query)
    priority_counts = {str(row[0].value): row[1] for row in result.all()}
    
    # Unassigned count
    unassigned_query = select(func.count(Conversation.id)).where(
        Conversation.agent_id.is_(None),
        Conversation.status.in_([MessageStatus.OPEN, MessageStatus.IN_PROGRESS])
    )
    result = await db.execute(unassigned_query)
    unassigned_count = result.scalar()
    
    return {
        "by_status": status_counts,
        "by_priority": priority_counts,
        "unassigned": unassigned_count
    }


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific conversation with all messages"""
    query = select(Conversation).where(
        Conversation.id == conversation_id
    ).options(
        selectinload(Conversation.customer),
        selectinload(Conversation.assigned_agent),
        selectinload(Conversation.messages)
    )
    
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update: ConversationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update conversation status, priority, or assign agent"""
    query = select(Conversation).where(
        Conversation.id == conversation_id
    ).options(
        selectinload(Conversation.customer),
        selectinload(Conversation.assigned_agent),
        selectinload(Conversation.messages)
    )
    
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(conversation)
    
    # Broadcast update
    await manager.broadcast_conversation_update({
        "id": conversation.id,
        "status": conversation.status.value,
        "priority": conversation.priority.value,
        "agent_id": conversation.agent_id
    })
    
    return conversation


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_agent_message(
    conversation_id: int,
    message: AgentMessageSend,
    db: AsyncSession = Depends(get_db)
):
    """Agent sends a message in a conversation"""
    # Verify conversation exists
    conv_query = select(Conversation).where(
        Conversation.id == conversation_id
    ).options(selectinload(Conversation.customer))
    
    result = await db.execute(conv_query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if conversation is assigned to another agent
    if conversation.agent_id is not None and conversation.agent_id != message.agent_id:
        raise HTTPException(
            status_code=403, 
            detail="This conversation is assigned to another agent. You cannot send messages here."
        )
    
    # Verify agent exists
    agent_query = select(Agent).where(Agent.id == message.agent_id)
    result = await db.execute(agent_query)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create the message
    db_message = Message(
        conversation_id=conversation_id,
        agent_id=message.agent_id,
        content=message.content,
        is_from_customer=False,
        priority=MessagePriority.MEDIUM
    )
    db.add(db_message)
    
    # Update conversation
    conversation.updated_at = datetime.utcnow()
    if conversation.agent_id is None:
        conversation.agent_id = message.agent_id
    if conversation.status == MessageStatus.OPEN:
        conversation.status = MessageStatus.IN_PROGRESS
    
    await db.commit()
    await db.refresh(db_message)
    
    # Broadcast new message
    await manager.broadcast_new_message({
        "id": db_message.id,
        "conversation_id": conversation_id,
        "agent_id": message.agent_id,
        "content": message.content,
        "is_from_customer": False,
        "priority": db_message.priority.value,
        "created_at": db_message.created_at.isoformat() + "Z",
        "agent_name": agent.name
    })
    
    return db_message


@router.post("/{conversation_id}/read")
async def mark_messages_read(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Mark all customer messages in a conversation as read"""
    query = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.is_from_customer == True,
        Message.read_at.is_(None)
    )
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    now = datetime.utcnow()
    for msg in messages:
        msg.read_at = now
    
    await db.commit()
    
    return {"marked_read": len(messages)}


@router.post("/{conversation_id}/assign/{agent_id}")
async def assign_conversation(
    conversation_id: int,
    agent_id: int,
    force: bool = Query(default=False, description="Force reassignment even if already assigned"),
    db: AsyncSession = Depends(get_db)
):
    """Assign a conversation to an agent"""
    # Verify conversation exists
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if already assigned to another agent
    if conversation.agent_id is not None and conversation.agent_id != agent_id and not force:
        # Get the current agent's name
        current_agent_result = await db.execute(
            select(Agent).where(Agent.id == conversation.agent_id)
        )
        current_agent = current_agent_result.scalar_one_or_none()
        agent_name = current_agent.name if current_agent else "another agent"
        raise HTTPException(
            status_code=409, 
            detail=f"This conversation is already assigned to {agent_name}. Use force=true to reassign."
        )
    
    # Verify agent exists
    agent_result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    conversation.agent_id = agent_id
    conversation.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Broadcast update
    await manager.broadcast_conversation_update({
        "id": conversation.id,
        "agent_id": agent_id,
        "agent_name": agent.name
    })
    
    return {"success": True, "agent_id": agent_id, "agent_name": agent.name}


@router.post("/{conversation_id}/release")
async def release_conversation(
    conversation_id: int,
    agent_id: int = Query(..., description="ID of the agent releasing the conversation"),
    db: AsyncSession = Depends(get_db)
):
    """Release a conversation from an agent (unassign)"""
    # Verify conversation exists
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if the requesting agent owns this conversation
    if conversation.agent_id != agent_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only release conversations assigned to you"
        )
    
    conversation.agent_id = None
    conversation.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Broadcast update
    await manager.broadcast_conversation_update({
        "id": conversation.id,
        "agent_id": None,
        "agent_name": None
    })
    
    return {"success": True, "message": "Conversation released"}
