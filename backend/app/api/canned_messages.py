from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from ..database import get_db
from ..models import CannedMessage
from ..schemas import CannedMessageCreate, CannedMessageUpdate, CannedMessageResponse

router = APIRouter(prefix="/canned-messages", tags=["canned-messages"])


@router.get("/", response_model=List[CannedMessageResponse])
async def get_canned_messages(
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all canned messages, optionally filtered by category"""
    query = select(CannedMessage)
    
    if category:
        query = query.where(CannedMessage.category == category)
    
    query = query.order_by(desc(CannedMessage.usage_count))
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all unique categories"""
    query = select(CannedMessage.category).distinct().where(
        CannedMessage.category.isnot(None)
    )
    result = await db.execute(query)
    categories = [row[0] for row in result.all() if row[0]]
    return categories


@router.get("/{message_id}", response_model=CannedMessageResponse)
async def get_canned_message(message_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific canned message"""
    result = await db.execute(
        select(CannedMessage).where(CannedMessage.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Canned message not found")
    
    return message


@router.post("/", response_model=CannedMessageResponse)
async def create_canned_message(
    message: CannedMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new canned message"""
    # Check if shortcut already exists
    if message.shortcut:
        result = await db.execute(
            select(CannedMessage).where(CannedMessage.shortcut == message.shortcut)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="A canned message with this shortcut already exists"
            )
    
    db_message = CannedMessage(**message.model_dump())
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    
    return db_message


@router.put("/{message_id}", response_model=CannedMessageResponse)
async def update_canned_message(
    message_id: int,
    message: CannedMessageUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a canned message"""
    result = await db.execute(
        select(CannedMessage).where(CannedMessage.id == message_id)
    )
    db_message = result.scalar_one_or_none()
    
    if not db_message:
        raise HTTPException(status_code=404, detail="Canned message not found")
    
    update_data = message.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_message, field, value)
    
    await db.commit()
    await db.refresh(db_message)
    
    return db_message


@router.delete("/{message_id}")
async def delete_canned_message(message_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a canned message"""
    result = await db.execute(
        select(CannedMessage).where(CannedMessage.id == message_id)
    )
    db_message = result.scalar_one_or_none()
    
    if not db_message:
        raise HTTPException(status_code=404, detail="Canned message not found")
    
    await db.delete(db_message)
    await db.commit()
    
    return {"success": True}


@router.post("/{message_id}/use", response_model=CannedMessageResponse)
async def use_canned_message(message_id: int, db: AsyncSession = Depends(get_db)):
    """Increment usage count when a canned message is used"""
    result = await db.execute(
        select(CannedMessage).where(CannedMessage.id == message_id)
    )
    db_message = result.scalar_one_or_none()
    
    if not db_message:
        raise HTTPException(status_code=404, detail="Canned message not found")
    
    db_message.usage_count += 1
    await db.commit()
    await db.refresh(db_message)
    
    return db_message
