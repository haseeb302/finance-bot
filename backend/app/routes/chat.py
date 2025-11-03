from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import structlog
import json
from json import JSONEncoder

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
    get_current_user_optional_from_session,
    get_current_user_from_session,
)
from app.services.openai import openai_service
from app.services.rag import rag_service, get_pinecone_embedding

router = APIRouter(prefix="/chat", tags=["Chat"])
security = HTTPBearer()

logger = structlog.get_logger(__name__)


class DateTimeEncoder(JSONEncoder):
    """Custom JSON encoder that handles datetime and Decimal objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def json_dumps_safe(data: Dict[str, Any]) -> str:
    """Safely serialize data to JSON, handling datetime objects."""
    return json.dumps(data, cls=DateTimeEncoder, ensure_ascii=False)


def require_authentication(current_user: Optional[dict]) -> dict:
    """Helper function to check if user is authenticated, raises 401 if not."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return current_user


@router.get("/", response_model=PaginatedChats)
async def get_chats(
    page: int = 1,
    page_size: int = settings.default_page_size,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Get user's chats with pagination."""
    current_user = require_authentication(current_user)

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
    chat_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Get specific chat by ID."""
    current_user = require_authentication(current_user)
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
    chat_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Delete a chat."""
    current_user = require_authentication(current_user)

    try:
        # Check if chat exists and user has access
        chat = await storage_service.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )

        if chat.get("user_id") and chat["user_id"] != current_user["user_id"]:
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
    current_user = require_authentication(current_user)

    try:
        # Check if chat exists and user has access
        chat = await storage_service.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )

        if chat.get("user_id") and chat["user_id"] != current_user["user_id"]:
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


async def _get_or_create_chat(
    message_text: str,
    chat_id: Optional[str],
    current_user: Optional[dict],
) -> Tuple[dict, str]:
    """
    Get existing chat or create new one.
    Returns tuple of (chat_dict, chat_id).
    Raises HTTPException on error.
    """
    if chat_id:
        chat = await storage_service.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found"
            )
        return chat, chat_id
    else:
        # Create new chat
        chat_data = ChatCreate(
            title=(
                message_text[:50] + "..." if len(message_text) > 50 else message_text
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
        return chat, chat["chat_id"]


async def _create_user_message(
    message_text: str,
    chat_id: str,
    current_user: Optional[dict],
) -> dict:
    """Create and save user message. Returns message dict. Raises HTTPException on error."""
    user_message_data = MessageCreate(
        role="user",
        content=message_text,
        user_id=current_user["user_id"] if current_user else None,
    )
    user_message = await storage_service.create_message(user_message_data, chat_id)
    logger.info(f"User message created: {user_message}")
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save user message",
        )
    return user_message


async def _get_rag_context_and_sources(
    message_text: str,
    chat_history: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Get RAG context and sources for a message.
    Returns tuple of (context_list, sources_list).
    Returns empty lists on error (logs error but doesn't raise).
    """
    try:
        query_embedding = await get_pinecone_embedding(message_text)
        similar_docs = await rag_service.pinecone_service.search_similar_documents(
            query_vector=query_embedding,
            top_k=5 * 2,  # Get more for filtering
        )

        # Filter documents by similarity threshold
        relevant_docs = []
        for doc in similar_docs:
            score = doc.get("score", 0)
            if score >= rag_service.similarity_threshold:
                content = doc.get("metadata", {}).get("text", "").lower()
                query_lower = message_text.lower()
                keyword_matches = sum(
                    1 for word in query_lower.split() if word in content
                )
                if keyword_matches > 0 or score > 0.7:
                    relevant_docs.append(doc)

        context = rag_service._prepare_context(relevant_docs)
        sources = rag_service._prepare_sources(relevant_docs)
        return context, sources

    except Exception as rag_error:
        logger.error(f"RAG context retrieval failed: {str(rag_error)}")
        return [], []


async def _create_error_message(
    chat_id: str,
    current_user: Optional[dict],
    error: str,
    error_type: str = "ai_generation_failed",
) -> dict:
    """Create and save error message. Returns message dict."""
    error_message_data = MessageCreate(
        role="assistant",
        content="I'm sorry, I'm having trouble processing your request right now. Please try again later.",
        user_id=current_user["user_id"] if current_user else None,
        metadata={
            "error": error,
            "error_type": error_type,
        },
    )
    return await storage_service.create_message(error_message_data, chat_id)


async def _stream_message_response(
    message_text: str,
    chat_id: Optional[str],
    current_user: Optional[dict],
):
    """Async generator for streaming message responses in SSE format."""
    try:
        # Get or create chat using helper
        original_chat_id = chat_id
        try:
            chat, chat_id = await _get_or_create_chat(
                message_text, chat_id, current_user
            )
            # If new chat was created (chat_id was None originally), send chat info to client
            if original_chat_id is None:
                chat_response = ChatResponse(
                    id=chat["chat_id"],
                    user_id=chat.get("user_id"),
                    title=chat["title"],
                    is_anonymous=chat.get("is_anonymous", False),
                    created_at=chat["created_at"],
                    updated_at=chat.get("updated_at"),
                    message_count=chat.get("message_count", 0),
                )
                # Use model_dump with json mode for proper datetime serialization
                yield f"data: {json_dumps_safe({'type': 'chat', 'chat': chat_response.model_dump(mode='json')})}\n\n"
        except HTTPException as e:
            yield f"data: {json_dumps_safe({'type': 'error', 'error': e.detail})}\n\n"
            return

        # Create user message using helper
        try:
            user_message = await _create_user_message(
                message_text, chat_id, current_user
            )
        except HTTPException as e:
            yield f"data: {json_dumps_safe({'type': 'error', 'error': e.detail})}\n\n"
            return

        # Get chat history for context
        chat_history = await storage_service.get_chat_history_for_context(
            chat_id, settings.chat_history_context_messages
        )
        logger.info(f"Retrieved {len(chat_history)} messages for streaming context")

        # Stream RAG response (includes context retrieval and OpenAI streaming)
        accumulated_content = ""
        sources_for_db = []  # Keep Decimal objects for DB storage
        sources_for_response = []  # Float values for JSON response

        try:
            async for chunk in rag_service.generate_response_with_rag_stream(
                query=message_text,
                chat_history=chat_history,
                top_k=5,
            ):
                if chunk.get("type") == "context_retrieving":
                    # Context retrieval started
                    yield f"data: {json_dumps_safe({'type': 'context_retrieving'})}\n\n"

                elif chunk.get("type") == "context_retrieved":
                    # Context retrieved - sources come with Decimal similarity scores
                    sources_for_db = chunk.get("sources", [])

                    # Convert Decimal to float for JSON response (SSE stream)
                    sources_for_response = []
                    for source in sources_for_db:
                        source_dict = {
                            "title": source.get("title", "Unknown"),
                            "source": source.get("source", ""),
                            "category": source.get("category", ""),
                            "similarity": float(source.get("similarity", 0)),
                        }
                        sources_for_response.append(source_dict)

                    yield f"data: {json_dumps_safe({
                        'type': 'context_retrieved',
                        'sources': sources_for_response,
                        'context_docs': chunk.get('context_docs', 0),
                    })}\n\n"

                elif chunk.get("type") == "token":
                    accumulated_content += chunk.get("content", "")
                    # Send token to client
                    yield f"data: {json_dumps_safe({'type': 'token', 'content': chunk.get('content', '')})}\n\n"

                elif chunk.get("type") == "done":
                    # Stream complete, save message to DB
                    # Keep Decimal similarity scores for DynamoDB (boto3 handles Decimal automatically)
                    sources_for_metadata = []
                    for source in sources_for_db:
                        source_dict = {
                            "title": source.get("title", "Unknown"),
                            "source": source.get("source", ""),
                            "category": source.get("category", ""),
                            "similarity": source.get(
                                "similarity", Decimal(0)
                            ),  # Keep Decimal for DB
                        }
                        sources_for_metadata.append(source_dict)

                    assistant_message_data = MessageCreate(
                        role="assistant",
                        content=accumulated_content,
                        user_id=current_user["user_id"] if current_user else None,
                        metadata={
                            "model": chunk.get("model"),
                            "sources": sources_for_metadata,
                        },
                    )

                    assistant_message = await storage_service.create_message(
                        assistant_message_data, chat_id
                    )

                    if assistant_message:
                        # Send final message to client
                        yield f"data: {json_dumps_safe({
                            'type': 'done',
                            'message': MessageResponse(
                                id=assistant_message['message_id'],
                                chat_id=assistant_message['chat_id'],
                                role=assistant_message['role'],
                                content=assistant_message['content'],
                                created_at=assistant_message['created_at'],
                                metadata=assistant_message.get('metadata', {}),
                            ).model_dump(mode='json'),
                            'sources': sources_for_response,
                        })}\n\n"
                    else:
                        yield f"data: {json_dumps_safe({'type': 'error', 'error': 'Failed to save assistant message'})}\n\n"

                elif chunk.get("type") == "error":
                    # Handle error from RAG streaming
                    error_content = chunk.get("error", "Unknown error")
                    error_message = await _create_error_message(
                        chat_id, current_user, error_content
                    )
                    if error_message:
                        yield f"data: {json_dumps_safe({
                            'type': 'error',
                            'message': MessageResponse(
                                id=error_message['message_id'],
                                chat_id=error_message['chat_id'],
                                role=error_message['role'],
                                content=error_message['content'],
                                created_at=error_message['created_at'],
                                metadata=error_message.get('metadata', {}),
                            ).model_dump(mode='json'),
                        })}\n\n"
                    else:
                        yield f"data: {json_dumps_safe({'type': 'error', 'error': error_content})}\n\n"

        except Exception as ai_error:
            logger.error(f"RAG streaming failed for chat {chat_id}: {str(ai_error)}")
            error_message = await _create_error_message(
                chat_id, current_user, str(ai_error)
            )
            if error_message:
                yield f"data: {json_dumps_safe({
                    'type': 'error',
                    'message': MessageResponse(
                        id=error_message['message_id'],
                        chat_id=error_message['chat_id'],
                        role=error_message['role'],
                        content=error_message['content'],
                        created_at=error_message['created_at'],
                        metadata=error_message.get('metadata', {}),
                    ).model_dump(mode='json'),
                })}\n\n"
            else:
                yield f"data: {json_dumps_safe({'type': 'error', 'error': str(ai_error)})}\n\n"

    except Exception as e:
        logger.error(f"Streaming error: {str(e)}", exc_info=True)
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(f"Streaming error traceback: {error_traceback}")
        yield f"data: {json_dumps_safe({'type': 'error', 'error': f'Failed to stream message: {str(e)}'})}\n\n"


@router.post("/message")
async def send_message(
    message_data: dict,
    current_user: Optional[dict] = Depends(get_current_user_optional_from_session),
):
    """Send message and get AI response. Supports streaming via stream parameter."""
    try:
        message_text = message_data.get("message", "")
        chat_id = message_data.get("chat_id")
        session_id = message_data.get("session_id")
        stream = message_data.get("stream", False)

        if not message_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content is required",
            )

        # If streaming requested, return streaming response
        if stream:
            return StreamingResponse(
                _stream_message_response(
                    message_text=message_text,
                    chat_id=chat_id,
                    current_user=current_user,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

        # Get or create chat using helper
        chat, chat_id = await _get_or_create_chat(message_text, chat_id, current_user)

        # Create user message using helper
        user_message = await _create_user_message(message_text, chat_id, current_user)

        # Get chat history for context
        chat_history = await storage_service.get_chat_history_for_context(
            chat_id, settings.chat_history_context_messages
        )
        logger.info(f"Retrieved {len(chat_history)} messages for context")
        print(f"Chat history for context: {chat_history}")

        # Get AI response using RAG
        try:
            logger.info(f"Starting RAG generation for message: {message_text[:50]}...")
            # Use RAG service to get context and generate response
            ai_response = await rag_service.generate_response_with_rag(
                query=message_text,
                chat_history=chat_history,
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
            # If AI fails, create an assistant error message using helper
            error_message = await _create_error_message(
                chat_id, current_user, str(ai_error)
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
