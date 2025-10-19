from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    is_anonymous: bool = False


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class ChatResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    is_anonymous: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    role: MessageRole = MessageRole.USER
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    chat_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    message: MessageResponse
    chat: Optional[ChatResponse] = None
    sources: Optional[List[Dict[str, Any]]] = None
    tokens_used: Optional[int] = None


class PaginatedMessages(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class PaginatedChats(BaseModel):
    chats: List[ChatResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class ChatSessionCreate(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=255)


class ChatSessionResponse(BaseModel):
    id: str
    session_id: str
    user_id: Optional[str] = None
    is_anonymous: bool
    created_at: datetime
    last_activity: datetime
    is_active: bool

    class Config:
        from_attributes = True
