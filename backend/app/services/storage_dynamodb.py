"""
DynamoDB Storage Service for FinanceBot
Handles all database operations using DynamoDB
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import structlog

from app.services.dynamodb import dynamodb_service
from app.core.settings import settings
from app.schemas.auth import UserCreate, UserUpdate, SessionCreate, SessionUpdate
from app.schemas.chat import (
    ChatCreate,
    MessageCreate,
    PaginatedMessages,
    PaginatedChats,
)
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseUpdate

logger = structlog.get_logger(__name__)


class DynamoDBStorageService:
    """Storage service using DynamoDB"""

    def __init__(self):
        self.db = dynamodb_service

    # User operations
    async def create_user(
        self, user_data: UserCreate, hashed_password: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new user."""
        try:
            user_id = str(uuid4())
            user_dict = {
                "user_id": user_id,
                "email": user_data.email,
                "username": user_data.username,
                "full_name": user_data.full_name,
                "hashed_password": hashed_password,
                "is_active": True,
            }

            result = await self.db.create_user(user_dict)
            if result:
                logger.info("User created successfully", user_id=user_id)
            return result
        except Exception as e:
            logger.error("Failed to create user", error=str(e))
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        return await self.db.get_user_by_email(email)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return await self.db.get_user(user_id)

    async def update_user(
        self, user_id: str, user_data: UserUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update user information."""
        try:
            update_data = user_data.dict(exclude_unset=True)

            # Handle password hashing
            if "password" in update_data:
                from app.utils.auth import get_password_hash

                update_data["hashed_password"] = get_password_hash(
                    update_data.pop("password")
                )

            success = await self.db.update_user(user_id, update_data)
            if success:
                return await self.get_user_by_id(user_id)
            return None
        except Exception as e:
            logger.error("Failed to update user", error=str(e))
            return None

    # Chat operations
    async def create_chat(
        self, chat_data: ChatCreate, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new chat."""
        try:
            chat_id = str(uuid4())
            chat_dict = {
                "chat_id": chat_id,
                "user_id": user_id,
                "title": chat_data.title,
                "is_anonymous": chat_data.is_anonymous,
            }

            result = await self.db.create_chat(chat_dict)
            if result:
                logger.info("Chat created successfully", chat_id=chat_id)
            return result
        except Exception as e:
            logger.error("Failed to create chat", error=str(e))
            return None

    async def get_chat_by_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat by ID."""
        return await self.db.get_chat(chat_id)

    async def get_user_chats(
        self, user_id: str, page: int = 1, page_size: int = settings.default_page_size
    ) -> PaginatedChats:
        """Get paginated chats for a user."""
        try:
            # Calculate pagination
            last_chat_id = None
            if page > 1:
                # For simplicity, we'll use a basic pagination approach
                # In production, you might want to implement cursor-based pagination
                pass

            chats = await self.db.get_user_chats(user_id, page_size, last_chat_id)

            # Convert to PaginatedChats format
            chat_list = []
            for chat in chats:
                chat_dict = {
                    "id": chat["chat_id"],
                    "user_id": chat.get("user_id"),
                    "title": chat["title"],
                    "is_anonymous": chat.get("is_anonymous", False),
                    "created_at": chat["created_at"],
                    "updated_at": chat["updated_at"],
                    "message_count": chat.get("message_count", 0),
                }
                chat_list.append(chat_dict)

            return PaginatedChats(
                chats=chat_list,
                total=len(chat_list),  # Simplified for now
                page=page,
                page_size=page_size,
                has_next=len(chat_list) == page_size,  # Simplified
                has_previous=page > 1,
            )
        except Exception as e:
            logger.error("Failed to get user chats", error=str(e))
            return PaginatedChats(
                chats=[],
                total=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False,
            )

    async def update_chat(self, chat_id: str, title: str) -> Optional[Dict[str, Any]]:
        """Update chat title."""
        try:
            success = await self.db.update_chat(chat_id, {"title": title})
            if success:
                return await self.get_chat_by_id(chat_id)
            return None
        except Exception as e:
            logger.error("Failed to update chat", error=str(e))
            return None

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat."""
        return await self.db.delete_chat(chat_id)

    # Message operations
    async def create_message(
        self, message_data: MessageCreate, chat_id: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new message."""
        try:
            message_dict = {
                "chat_id": chat_id,
                "role": message_data.role,
                "content": message_data.content,
                "metadata": message_data.metadata or {},
                "user_id": message_data.user_id,
            }

            logger.info("Creating message", message_dict=message_dict, chat_id=chat_id)
            result = await self.db.create_message(message_dict)
            if result:
                logger.info(
                    "Message created successfully",
                    chat_id=chat_id,
                    message_id=result.get("message_id"),
                )
            else:
                logger.error(
                    "Failed to create message - no result returned", chat_id=chat_id
                )
            return result
        except Exception as e:
            logger.error(
                "Failed to create message",
                error=str(e),
                chat_id=chat_id,
                message_data=message_data.dict(),
            )
            return None

    async def get_chat_messages(
        self, chat_id: str, page: int = 1, page_size: int = settings.default_page_size
    ) -> PaginatedMessages:
        """Get paginated messages for a chat."""
        try:
            # Get all messages (oldest first for proper pagination)
            all_messages = await self.db.get_chat_messages(
                chat_id, 1000
            )  # Get all messages

            # Calculate pagination for "load more" at top
            total_messages = len(all_messages)

            if page == 1:
                # First page: get the newest messages (last page_size messages)
                start_index = max(0, total_messages - page_size)
                end_index = total_messages
                messages = all_messages[start_index:]
                has_next = start_index > 0
            else:
                # Load more: get older messages (previous page_size messages)
                start_index = max(0, total_messages - (page * page_size))
                end_index = total_messages - ((page - 1) * page_size)
                messages = all_messages[start_index:end_index]
                has_next = start_index > 0

            logger.info(
                f"Pagination debug - Chat: {chat_id}, Page: {page}, PageSize: {page_size}"
            )
            logger.info(
                f"Total messages: {total_messages}, Start: {start_index}, End: {end_index}"
            )
            logger.info(f"Returning {len(messages)} messages, has_next: {has_next}")

            # Convert to PaginatedMessages format
            message_list = []
            for message in messages:
                message_dict = {
                    "id": message["message_id"],
                    "chat_id": message["chat_id"],
                    "role": message["role"],
                    "content": message["content"],
                    "created_at": message["created_at"],
                    "metadata": message.get("metadata", {}),
                }
                message_list.append(message_dict)

            return PaginatedMessages(
                messages=message_list,
                total=total_messages,
                page=page,
                page_size=page_size,
                has_next=has_next,
                has_previous=page > 1,
            )
        except Exception as e:
            logger.error("Failed to get chat messages", error=str(e))
            return PaginatedMessages(
                messages=[],
                total=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False,
            )

    # Knowledge base operations (simplified for now)
    async def create_knowledge_document(
        self,
        doc_data: KnowledgeBaseCreate,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new knowledge base document."""
        try:
            doc_id = str(uuid4())
            doc_dict = {
                "doc_id": doc_id,
                "title": doc_data.title,
                "content": doc_data.content,
                "source": doc_data.source,
                "category": doc_data.category,
                "created_by": user_id,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # For now, we'll store knowledge base documents in a simple way
            # In production, you might want to use a separate table
            logger.info("Knowledge document created", doc_id=doc_id)
            return doc_dict
        except Exception as e:
            logger.error("Failed to create knowledge document", error=str(e))
            return None

    async def get_knowledge_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get knowledge base document by ID."""
        # Simplified implementation
        return None

    async def get_knowledge_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get paginated knowledge base documents."""
        # Simplified implementation
        return []

    async def update_knowledge_document(
        self, doc_id: str, doc_data: KnowledgeBaseUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update knowledge base document."""
        # Simplified implementation
        return None

    async def delete_knowledge_document(self, doc_id: str) -> bool:
        """Delete knowledge base document."""
        # Simplified implementation
        return True

    # Refresh token operations (simplified for now)
    async def create_refresh_token(
        self, token: str, user_id: str, expires_at: datetime
    ) -> Optional[Dict[str, Any]]:
        """Create a refresh token."""
        try:
            refresh_token_dict = {
                "token_id": str(uuid4()),
                "token": token,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "is_revoked": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # For now, we'll store refresh tokens in a simple way
            # In production, you might want to use a separate table
            logger.info("Refresh token created", user_id=user_id)
            return refresh_token_dict
        except Exception as e:
            logger.error("Failed to create refresh token", error=str(e))
            return None

    async def get_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token."""
        # Simplified implementation
        return None

    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token."""
        # Simplified implementation
        return True

    # Session operations
    async def create_session(
        self, session_data: SessionCreate, expires_at: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new session."""
        try:
            session_dict = {
                "user_id": session_data.user_id,
                "access_token": session_data.access_token,
                "refresh_token": session_data.refresh_token,
                "expires_at": expires_at,
                "device_info": session_data.device_info,
                "ip_address": session_data.ip_address,
            }

            logger.info("Creating session", user_id=session_data.user_id)
            result = await self.db.create_session(session_dict)
            if result:
                logger.info(
                    "Session created successfully", session_id=result.get("session_id")
                )
            return result
        except Exception as e:
            logger.error("Failed to create session", error=str(e))
            return None

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        try:
            return await self.db.get_session(session_id)
        except Exception as e:
            logger.error("Failed to get session", error=str(e))
            return None

    async def update_session(self, session_id: str, update_data) -> bool:
        """Update session."""
        try:
            # Handle both SessionUpdate objects and dictionaries
            if isinstance(update_data, dict):
                update_dict = update_data
            else:
                update_dict = update_data.dict(exclude_unset=True)
            return await self.db.update_session(session_id, update_dict)
        except Exception as e:
            logger.error("Failed to update session", error=str(e))
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        try:
            return await self.db.delete_session(session_id)
        except Exception as e:
            logger.error("Failed to delete session", error=str(e))
            return False

    async def get_user_sessions(
        self, user_id: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        try:
            return await self.db.get_user_sessions(user_id, active_only)
        except Exception as e:
            logger.error("Failed to get user sessions", error=str(e))
            return []

    async def invalidate_user_sessions(self, user_id: str) -> bool:
        """Invalidate all sessions for a user."""
        try:
            return await self.db.invalidate_user_sessions(user_id)
        except Exception as e:
            logger.error("Failed to invalidate user sessions", error=str(e))
            return False

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            return await self.db.cleanup_expired_sessions()
        except Exception as e:
            logger.error("Failed to cleanup expired sessions", error=str(e))
            return 0


# Global instance
storage_service = DynamoDBStorageService()
