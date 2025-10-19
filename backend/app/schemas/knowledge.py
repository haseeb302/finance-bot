from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)


class KnowledgeBaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    source: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    title: str
    content: str
    source: Optional[str] = None
    category: Optional[str] = None
    embedding_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class KnowledgeBaseSearch(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(10, ge=1, le=50)
    category: Optional[str] = None


class KnowledgeBaseSearchResult(BaseModel):
    id: int
    title: str
    content: str
    source: Optional[str] = None
    category: Optional[str] = None
    score: float
    similarity: float


class BulkKnowledgeBaseCreate(BaseModel):
    items: List[KnowledgeBaseCreate] = Field(..., min_items=1, max_items=100)


class KnowledgeBaseStats(BaseModel):
    total_documents: int
    active_documents: int
    categories: List[str]
    last_updated: Optional[datetime] = None
