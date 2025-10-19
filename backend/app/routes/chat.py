from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import structlog

from app.schemas.chat import (
    ChatCreate,
    MessageCreate,
    PaginatedMessages,
    PaginatedChats,
    ChatResponse,
    MessageResponse,
    ChatSessionResponse,
)
from app.services.storage_dynamodb import storage_service
from app.core.settings import settings
from app.utils.auth import (
    get_current_active_user,
    get_current_user_optional,
    get_current_user_from_session,
    get_current_user_optional_from_session,
)
from app.services.openai import openai_service
from app.services.rag import rag_service

router = APIRouter(prefix="/chat", tags=["Chat"])
security = HTTPBearer()

logger = structlog.get_logger(__name__)


@router.get("/", response_model=PaginatedChats)
async def get_chats(
    page: int = 1,
    page_size: int = settings.default_page_size,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Get user's chats with pagination."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view chats",
        )

    try:
        chats = await storage_service.get_user_chats(
            current_user["user_id"], page, page_size
        )
        return chats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chats: {str(e)}",
        )


@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Get user's chats with pagination."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view chats",
        )

    """Create a new chat."""
    try:
        chat = await storage_service.create_chat(
            chat_data, current_user["user_id"] if current_user else None
        )

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat",
            )

        return ChatResponse(
            id=chat["chat_id"],
            user_id=chat.get("user_id"),
            title=chat["title"],
            is_anonymous=chat.get("is_anonymous", False),
            created_at=chat["created_at"],
            updated_at=chat.get("updated_at"),
            message_count=chat.get("message_count", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}",
        )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str, current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get specific chat by ID."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view chat",
        )

    """Get specific chat by ID."""
    try:
        chat = await storage_service.get_chat_by_id(chat_id)

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )

        # Check if user has access to this chat
        if (
            chat.get("user_id")
            and current_user
            and chat["user_id"] != current_user["user_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat",
            )

        return ChatResponse(
            id=chat["chat_id"],
            user_id=chat.get("user_id"),
            title=chat["title"],
            is_anonymous=chat.get("is_anonymous", False),
            created_at=chat["created_at"],
            updated_at=chat.get("updated_at"),
            message_count=chat.get("message_count", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat: {str(e)}",
        )


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    title: str,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Update chat title."""
    try:
        # Check if chat exists and user has access
        chat = await storage_service.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )

        if (
            chat.get("user_id")
            and current_user
            and chat["user_id"] != current_user["user_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat",
            )

        updated_chat = await storage_service.update_chat(chat_id, title)

        if not updated_chat:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update chat",
            )

        return ChatResponse(
            id=updated_chat["chat_id"],
            user_id=updated_chat.get("user_id"),
            title=updated_chat["title"],
            is_anonymous=updated_chat.get("is_anonymous", False),
            created_at=updated_chat["created_at"],
            updated_at=updated_chat.get("updated_at"),
            message_count=updated_chat.get("message_count", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat: {str(e)}",
        )


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str, current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Delete a chat."""
    try:
        # Check if chat exists and user has access
        chat = await storage_service.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )

        if (
            chat.get("user_id")
            and current_user
            and chat["user_id"] != current_user["user_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat",
            )

        success = await storage_service.delete_chat(chat_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete chat",
            )

        return {"message": "Chat deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}",
        )


@router.get("/{chat_id}/messages", response_model=PaginatedMessages)
async def get_messages(
    chat_id: str,
    page: int = 1,
    page_size: int = settings.default_page_size,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Get chat messages with pagination."""
    try:
        # Check if chat exists and user has access
        chat = await storage_service.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )

        if (
            chat.get("user_id")
            and current_user
            and chat["user_id"] != current_user["user_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat",
            )

        messages = await storage_service.get_chat_messages(chat_id, page, page_size)
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


@router.post("/message")
async def send_message(
    message_data: dict,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Send message and get AI response."""
    try:
        message_text = message_data.get("message", "")
        chat_id = message_data.get("chat_id")
        session_id = message_data.get("session_id")

        if not message_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content is required",
            )

        # Create or get chat
        if chat_id:
            chat = await storage_service.get_chat_by_id(chat_id)
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
                )
        else:
            # Create new chat for this message
            chat_data = ChatCreate(
                title=(
                    message_text[:50] + "..."
                    if len(message_text) > 50
                    else message_text
                ),
                is_anonymous=current_user is None,
            )
            chat = await storage_service.create_chat(
                chat_data, current_user["user_id"] if current_user else None
            )
            logger.info(f"Chat created: {chat}")
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create chat",
                )
            chat_id = chat["chat_id"]

        # Create user message
        user_message_data = MessageCreate(
            role="user",
            content=message_text,
            user_id=current_user["user_id"] if current_user else None,
        )
        user_message = await storage_service.create_message(user_message_data, chat_id)
        logger.info(f"User message: {user_message}")
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user message",
            )

        # Get AI response using RAG
        try:
            logger.info(f"Starting RAG generation for message: {message_text[:50]}...")
            # Use RAG service to get context and generate response
            ai_response = await rag_service.generate_response_with_rag(
                query=message_text,
                chat_history=None,  # Could add chat history here
                top_k=5,
            )
            logger.info(f"RAG generation completed successfully for chat {chat_id}")

            # Create assistant message
            assistant_message_data = MessageCreate(
                role="assistant",
                content=ai_response["content"],
                user_id=current_user["user_id"] if current_user else None,
                metadata={
                    "tokens_used": ai_response.get("tokens_used"),
                    "model": ai_response.get("model"),
                    "sources": ai_response.get("sources", []),
                },
            )

            assistant_message = await storage_service.create_message(
                assistant_message_data, chat_id
            )
            if not assistant_message:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save assistant message",
                )

            return {
                "message": MessageResponse(
                    id=assistant_message["message_id"],
                    chat_id=assistant_message["chat_id"],
                    role=assistant_message["role"],
                    content=assistant_message["content"],
                    created_at=assistant_message["created_at"],
                    metadata=assistant_message.get("metadata", {}),
                ),
                "chat": ChatResponse(
                    id=chat["chat_id"],
                    user_id=chat.get("user_id"),
                    title=chat["title"],
                    is_anonymous=chat.get("is_anonymous", False),
                    created_at=chat["created_at"],
                    updated_at=chat.get("updated_at"),
                    message_count=chat.get("message_count", 0),
                ),
                "sources": ai_response.get("sources", []),
                "tokens_used": ai_response.get("tokens_used"),
            }

        except Exception as ai_error:
            logger.error(f"RAG generation failed for chat {chat_id}: {str(ai_error)}")
            # If AI fails, create an assistant error message
            error_message_data = MessageCreate(
                role="assistant",
                content="I'm sorry, I'm having trouble processing your request right now. Please try again later.",
                user_id=current_user["user_id"] if current_user else None,
                metadata={
                    "error": str(ai_error),
                    "error_type": "ai_generation_failed",
                },
            )

            error_message = await storage_service.create_message(
                error_message_data, chat_id
            )

            return {
                "message": MessageResponse(
                    id=error_message["message_id"],
                    chat_id=error_message["chat_id"],
                    role=error_message["role"],
                    content=error_message["content"],
                    created_at=error_message["created_at"],
                    metadata=error_message.get("metadata", {}),
                ),
                "chat": ChatResponse(
                    id=chat["chat_id"],
                    user_id=chat.get("user_id"),
                    title=chat["title"],
                    is_anonymous=chat.get("is_anonymous", False),
                    created_at=chat["created_at"],
                    updated_at=chat.get("updated_at"),
                    message_count=chat.get("message_count", 0),
                ),
                "sources": [],
                "tokens_used": 0,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )
