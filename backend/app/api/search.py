from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional

from ..database import get_db
from ..models import Conversation, Message, Customer, MessagePriority, MessageStatus
from ..schemas import (
    SearchQuery, SearchResult, ConversationListResponse, 
    CustomerResponse, MessagePriorityEnum, MessageStatusEnum
)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    search_in: str = Query("all", description="Where to search: all, messages, customers"),
    priority: Optional[MessagePriorityEnum] = None,
    status: Optional[MessageStatusEnum] = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search across messages and customers.
    Supports filtering by priority and status.
    """
    search_term = f"%{q}%"
    results = {
        "conversations": [],
        "customers": [],
        "total_results": 0
    }
    
    # Search in messages/conversations
    if search_in in ["all", "messages"]:
        conv_query = select(Conversation).options(
            selectinload(Conversation.customer),
            selectinload(Conversation.assigned_agent),
            selectinload(Conversation.messages)
        ).join(Message).where(
            Message.content.ilike(search_term)
        )
        
        if priority:
            conv_query = conv_query.where(Conversation.priority == priority)
        
        if status:
            conv_query = conv_query.where(Conversation.status == status)
        
        conv_query = conv_query.distinct().order_by(
            desc(Conversation.updated_at)
        ).limit(limit)
        
        result = await db.execute(conv_query)
        conversations = result.scalars().all()
        
        for conv in conversations:
            last_message = conv.messages[-1] if conv.messages else None
            unread_count = sum(1 for m in conv.messages if m.is_from_customer and not m.read_at)
            
            results["conversations"].append({
                "id": conv.id,
                "customer_id": conv.customer_id,
                "agent_id": conv.agent_id,
                "status": conv.status.value,
                "priority": conv.priority.value,
                "subject": conv.subject,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "customer": {
                    "id": conv.customer.id,
                    "name": conv.customer.name,
                    "email": conv.customer.email
                } if conv.customer else None,
                "assigned_agent": {
                    "id": conv.assigned_agent.id,
                    "name": conv.assigned_agent.name
                } if conv.assigned_agent else None,
                "last_message": {
                    "id": last_message.id,
                    "content": last_message.content,
                    "is_from_customer": last_message.is_from_customer,
                    "created_at": last_message.created_at.isoformat()
                } if last_message else None,
                "unread_count": unread_count
            })
    
    # Search in customers
    if search_in in ["all", "customers"]:
        customer_query = select(Customer).where(
            or_(
                Customer.name.ilike(search_term),
                Customer.email.ilike(search_term),
                Customer.phone.ilike(search_term)
            )
        ).order_by(desc(Customer.last_activity)).limit(limit)
        
        result = await db.execute(customer_query)
        customers = result.scalars().all()
        
        for customer in customers:
            results["customers"].append({
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "account_status": customer.account_status,
                "loan_status": customer.loan_status,
                "loan_amount": customer.loan_amount,
                "account_created": customer.account_created.isoformat(),
                "last_activity": customer.last_activity.isoformat()
            })
    
    results["total_results"] = len(results["conversations"]) + len(results["customers"])
    
    return results


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db)
):
    """Get search suggestions based on partial query"""
    search_term = f"%{q}%"
    
    suggestions = []
    
    # Get customer name suggestions
    customer_query = select(Customer.name).where(
        Customer.name.ilike(search_term)
    ).distinct().limit(5)
    
    result = await db.execute(customer_query)
    for row in result.all():
        suggestions.append({"type": "customer", "value": row[0]})
    
    # Get email suggestions
    email_query = select(Customer.email).where(
        Customer.email.ilike(search_term)
    ).distinct().limit(5)
    
    result = await db.execute(email_query)
    for row in result.all():
        suggestions.append({"type": "email", "value": row[0]})
    
    return suggestions[:10]
