from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models import Agent
from ..schemas import AgentCreate, AgentResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=List[AgentResponse])
async def get_agents(db: AsyncSession = Depends(get_db)):
    """Get all agents"""
    result = await db.execute(select(Agent))
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific agent by ID"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new agent"""
    # Check if agent with email already exists
    result = await db.execute(select(Agent).where(Agent.email == agent.email))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this email already exists")
    
    db_agent = Agent(**agent.model_dump())
    db.add(db_agent)
    await db.commit()
    await db.refresh(db_agent)
    
    return db_agent


@router.put("/{agent_id}/online", response_model=AgentResponse)
async def set_agent_online(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Set agent as online"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.is_online = True
    await db.commit()
    await db.refresh(agent)
    
    return agent


@router.put("/{agent_id}/offline", response_model=AgentResponse)
async def set_agent_offline(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Set agent as offline"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.is_online = False
    await db.commit()
    await db.refresh(agent)
    
    return agent
