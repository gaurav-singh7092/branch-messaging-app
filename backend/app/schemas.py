from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum


class MessagePriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatusEnum(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Customer Schemas
class CustomerBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    account_status: Optional[str] = "active"
    loan_status: Optional[str] = None
    loan_amount: Optional[float] = None
    profile_notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    account_status: Optional[str] = None
    loan_status: Optional[str] = None
    loan_amount: Optional[float] = None
    profile_notes: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: int
    account_created: datetime
    last_activity: datetime

    class Config:
        from_attributes = True


# Agent Schemas
class AgentBase(BaseModel):
    name: str
    email: str
    avatar_url: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: int
    is_online: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Message Schemas
class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    conversation_id: Optional[int] = None
    customer_id: Optional[int] = None
    is_from_customer: bool = True


class MessageSend(BaseModel):
    content: str
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None


class AgentMessageSend(BaseModel):
    content: str
    conversation_id: int
    agent_id: int


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    customer_id: Optional[int]
    agent_id: Optional[int]
    is_from_customer: bool
    priority: MessagePriorityEnum
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


# Conversation Schemas
class ConversationBase(BaseModel):
    subject: Optional[str] = None


class ConversationCreate(ConversationBase):
    customer_id: int


class ConversationUpdate(BaseModel):
    status: Optional[MessageStatusEnum] = None
    priority: Optional[MessagePriorityEnum] = None
    agent_id: Optional[int] = None


class ConversationResponse(ConversationBase):
    id: int
    customer_id: int
    agent_id: Optional[int]
    status: MessageStatusEnum
    priority: MessagePriorityEnum
    created_at: datetime
    updated_at: datetime
    customer: Optional[CustomerResponse] = None
    assigned_agent: Optional[AgentResponse] = None
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    id: int
    customer_id: int
    agent_id: Optional[int]
    status: MessageStatusEnum
    priority: MessagePriorityEnum
    subject: Optional[str]
    created_at: datetime
    updated_at: datetime
    customer: Optional[CustomerResponse] = None
    assigned_agent: Optional[AgentResponse] = None
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0

    class Config:
        from_attributes = True


# Canned Message Schemas
class CannedMessageBase(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    shortcut: Optional[str] = None


class CannedMessageCreate(CannedMessageBase):
    pass


class CannedMessageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    shortcut: Optional[str] = None


class CannedMessageResponse(CannedMessageBase):
    id: int
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    type: str
    data: dict


# Search Schemas
class SearchQuery(BaseModel):
    query: str
    search_in: List[str] = ["messages", "customers"]
    priority: Optional[MessagePriorityEnum] = None
    status: Optional[MessageStatusEnum] = None
    limit: int = 50


class SearchResult(BaseModel):
    conversations: List[ConversationListResponse] = []
    customers: List[CustomerResponse] = []
    total_results: int = 0
