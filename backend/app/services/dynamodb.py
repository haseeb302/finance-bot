"""
DynamoDB Service Layer for FinanceBot
Handles all database operations for users, chats, and messages
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.dynamodb.conditions import Key, Attr
from pydantic import BaseModel, Field

from app.core.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class DynamoDBService:
    """DynamoDB service for managing chat application data"""

    def __init__(self):
        self.region = settings.dynamodb_region
        self.endpoint_url = settings.dynamodb_endpoint_url
        self.table_prefix = settings.dynamodb_table_prefix

        # Initialize DynamoDB client
        try:
            if self.endpoint_url and "localhost" in self.endpoint_url:
                # Local development
                self.dynamodb = boto3.resource(
                    "dynamodb",
                    region_name=self.region,
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=settings.dynamodb_access_key,
                    aws_secret_access_key=settings.dynamodb_secret_key,
                )
            else:
                # Production AWS
                self.dynamodb = boto3.resource("dynamodb", region_name=self.region)

            self.client = self.dynamodb.meta.client
            logger.info(
                "DynamoDB client initialized",
                region=self.region,
                endpoint=self.endpoint_url,
            )

        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error("Failed to initialize DynamoDB client", error=str(e))
            raise

    def get_table_name(self, table_type: str) -> str:
        """Get full table name with prefix"""
        return f"{self.table_prefix}-{table_type}"

    async def _cleanup_old_tables(self):
        """Clean up old tables with financebot prefix"""
        try:
            old_tables = [
                "financebot-users",
                "financebot-chats",
                "financebot-messages",
            ]

            for table_name in old_tables:
                try:
                    self.client.describe_table(TableName=table_name)
                    logger.info(f"Dropping old table: {table_name}")
                    self.client.delete_table(TableName=table_name)

                    # Wait for table to be deleted
                    waiter = self.client.get_waiter("table_not_exists")
                    waiter.wait(TableName=table_name)
                    logger.info(f"Old table {table_name} deleted successfully")
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ResourceNotFoundException":
                        logger.info(f"Old table {table_name} does not exist, skipping")
                    else:
                        logger.warning(f"Failed to delete old table {table_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old tables: {e}")

    async def create_tables(self) -> bool:
        """Create all required tables if they don't exist"""
        try:
            # First, clean up old tables with financebot prefix if they exist
            # await self._cleanup_old_tables()
            tables_to_create = [
                {
                    "name": "users",
                    "key_schema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
                    "attribute_definitions": [
                        {"AttributeName": "user_id", "AttributeType": "S"}
                    ],
                },
                {
                    "name": "chats",
                    "key_schema": [{"AttributeName": "chat_id", "KeyType": "HASH"}],
                    "attribute_definitions": [
                        {"AttributeName": "chat_id", "AttributeType": "S"}
                    ],
                },
                {
                    "name": "messages",
                    "key_schema": [
                        {"AttributeName": "chat_id", "KeyType": "HASH"},
                        {"AttributeName": "timestamp_message_id", "KeyType": "RANGE"},
                    ],
                    "attribute_definitions": [
                        {"AttributeName": "chat_id", "AttributeType": "S"},
                        {"AttributeName": "timestamp_message_id", "AttributeType": "S"},
                    ],
                },
                {
                    "name": "sessions",
                    "key_schema": [{"AttributeName": "session_id", "KeyType": "HASH"}],
                    "attribute_definitions": [
                        {"AttributeName": "session_id", "AttributeType": "S"},
                        {"AttributeName": "user_id", "AttributeType": "S"},
                        {"AttributeName": "expires_at", "AttributeType": "S"},
                    ],
                    "global_secondary_indexes": [
                        {
                            "IndexName": "user-sessions-index",
                            "KeySchema": [
                                {"AttributeName": "user_id", "KeyType": "HASH"},
                                {"AttributeName": "expires_at", "KeyType": "RANGE"},
                            ],
                            "Projection": {"ProjectionType": "ALL"},
                        }
                    ],
                },
            ]

            for table_config in tables_to_create:
                table_name = self.get_table_name(table_config["name"])

                # Check if table exists
                try:
                    self.client.describe_table(TableName=table_name)
                    logger.info(f"Table {table_name} already exists")
                    continue
                except ClientError as e:
                    if e.response["Error"]["Code"] != "ResourceNotFoundException":
                        raise

                # Create table
                create_params = {
                    "TableName": table_name,
                    "KeySchema": table_config["key_schema"],
                    "AttributeDefinitions": table_config["attribute_definitions"],
                    "BillingMode": "PAY_PER_REQUEST",
                }

                # Add GSI if present
                if "global_secondary_indexes" in table_config:
                    create_params["GlobalSecondaryIndexes"] = table_config[
                        "global_secondary_indexes"
                    ]

                table = self.dynamodb.create_table(**create_params)

                # Wait for table to be created
                table.wait_until_exists()
                logger.info(f"Table {table_name} created successfully")

            return True

        except Exception as e:
            logger.error("Failed to create tables", error=str(e))
            return False

    # User Operations
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            table = self.dynamodb.Table(self.get_table_name("users"))

            user_item = {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "username": user_data.get("username"),
                "hashed_password": user_data["hashed_password"],
                "is_active": user_data.get("is_active", True),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None,
            }

            table.put_item(Item=user_item)
            logger.info("User created successfully", user_id=user_data["user_id"])
            return user_item

        except Exception as e:
            logger.error("Failed to create user", error=str(e))
            return None

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            table = self.dynamodb.Table(self.get_table_name("users"))
            response = table.get_item(Key={"user_id": user_id})
            return response.get("Item")
        except Exception as e:
            logger.error("Failed to get user", error=str(e))
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email using scan (not efficient for large datasets)"""
        try:
            table = self.dynamodb.Table(self.get_table_name("users"))
            response = table.scan(FilterExpression=Attr("email").eq(email))
            items = response.get("Items", [])
            return items[0] if items else None
        except Exception as e:
            logger.error("Failed to get user by email", error=str(e))
            return None

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            table = self.dynamodb.Table(self.get_table_name("users"))

            # Build update expression
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}

            for key, value in update_data.items():
                if key != "user_id":  # Don't update the key
                    update_expression += f"#{key} = :{key}, "
                    expression_attribute_values[f":{key}"] = value
                    expression_attribute_names[f"#{key}"] = key

            # Remove trailing comma
            update_expression = update_expression.rstrip(", ")

            table.update_item(
                Key={"user_id": user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
            )

            logger.info("User updated successfully", user_id=user_id)
            return True

        except Exception as e:
            logger.error("Failed to update user", error=str(e))
            return False

    # Chat Operations
    async def create_chat(self, chat_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new chat"""
        try:
            table = self.dynamodb.Table(self.get_table_name("chats"))

            chat_item = {
                "chat_id": chat_data["chat_id"],
                "user_id": chat_data.get("user_id"),  # None for anonymous chats
                "title": chat_data.get("title", "New Chat"),
                "is_anonymous": chat_data.get("is_anonymous", False),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "message_count": 0,
            }

            table.put_item(Item=chat_item)
            logger.info("Chat created successfully", chat_id=chat_data["chat_id"])
            return chat_item

        except Exception as e:
            logger.error("Failed to create chat", error=str(e))
            return None

    async def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat by ID"""
        try:
            table = self.dynamodb.Table(self.get_table_name("chats"))
            response = table.get_item(Key={"chat_id": chat_id})
            return response.get("Item")
        except Exception as e:
            logger.error("Failed to get chat", error=str(e))
            return None

    async def get_user_chats(
        self, user_id: str, limit: int = 15, last_chat_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's chats with pagination"""
        try:
            table = self.dynamodb.Table(self.get_table_name("chats"))

            # Scan with filter for user_id
            scan_kwargs = {
                "FilterExpression": Attr("user_id").eq(user_id),
                "Limit": limit,
            }

            if last_chat_id:
                scan_kwargs["ExclusiveStartKey"] = {"chat_id": last_chat_id}

            response = table.scan(**scan_kwargs)
            return response.get("Items", [])

        except Exception as e:
            logger.error("Failed to get user chats", error=str(e))
            return []

    async def update_chat(self, chat_id: str, update_data: Dict[str, Any]) -> bool:
        """Update chat data"""
        try:
            table = self.dynamodb.Table(self.get_table_name("chats"))

            # Build update expression
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}

            for key, value in update_data.items():
                if key != "chat_id":  # Don't update the key
                    update_expression += f"#{key} = :{key}, "
                    expression_attribute_values[f":{key}"] = value
                    expression_attribute_names[f"#{key}"] = key

            # Always update updated_at
            update_expression += "#updated_at = :updated_at"
            expression_attribute_values[":updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            expression_attribute_names["#updated_at"] = "updated_at"

            table.update_item(
                Key={"chat_id": chat_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
            )

            logger.info("Chat updated successfully", chat_id=chat_id)
            return True

        except Exception as e:
            logger.error("Failed to update chat", error=str(e))
            return False

    async def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat and all its messages"""
        try:
            # Delete all messages first
            await self.delete_chat_messages(chat_id)

            # Delete chat
            table = self.dynamodb.Table(self.get_table_name("chats"))
            table.delete_item(Key={"chat_id": chat_id})

            logger.info("Chat deleted successfully", chat_id=chat_id)
            return True

        except Exception as e:
            logger.error("Failed to delete chat", error=str(e))
            return False

    # Message Operations
    async def create_message(
        self, message_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new message"""
        try:
            table_name = self.get_table_name("messages")
            logger.info(
                "Creating message in table",
                table_name=table_name,
                message_data=message_data,
            )

            table = self.dynamodb.Table(table_name)

            # Generate timestamp_message_id for sorting
            timestamp = datetime.now(timezone.utc)
            message_id = str(uuid4())
            timestamp_message_id = f"{timestamp.isoformat()}#{message_id}"

            message_item = {
                "chat_id": message_data["chat_id"],
                "timestamp_message_id": timestamp_message_id,
                "message_id": message_id,
                "user_id": message_data.get("user_id"),
                "role": message_data["role"],
                "content": message_data["content"],
                "created_at": timestamp.isoformat(),
                "metadata": message_data.get("metadata", {}),
            }

            logger.info("Putting message item", message_item=message_item)
            table.put_item(Item=message_item)

            # Update chat message count
            await self.increment_chat_message_count(message_data["chat_id"])

            logger.info("Message created successfully", message_id=message_id)
            return message_item

        except Exception as e:
            logger.error("Failed to create message", error=str(e))
            return None

    async def get_chat_messages(
        self, chat_id: str, limit: int = 15, last_message_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get chat messages with pagination"""
        try:
            table = self.dynamodb.Table(self.get_table_name("messages"))

            query_kwargs = {
                "KeyConditionExpression": Key("chat_id").eq(chat_id),
                "ScanIndexForward": True,  # Get oldest messages first for proper pagination
                "Limit": limit,
            }

            if last_message_id:
                # Parse the last message's timestamp_message_id
                last_timestamp_message_id = last_message_id
                query_kwargs["ExclusiveStartKey"] = {
                    "chat_id": chat_id,
                    "timestamp_message_id": last_timestamp_message_id,
                }

            response = table.query(**query_kwargs)
            return response.get("Items", [])

        except Exception as e:
            logger.error("Failed to get chat messages", error=str(e))
            return []

    async def delete_chat_messages(self, chat_id: str) -> bool:
        """Delete all messages for a chat"""
        try:
            table = self.dynamodb.Table(self.get_table_name("messages"))

            # Get all messages for the chat
            response = table.query(
                KeyConditionExpression=Key("chat_id").eq(chat_id),
                ProjectionExpression="timestamp_message_id",
            )

            # Delete messages in batches
            with table.batch_writer() as batch:
                for item in response.get("Items", []):
                    batch.delete_item(
                        Key={
                            "chat_id": chat_id,
                            "timestamp_message_id": item["timestamp_message_id"],
                        }
                    )

            logger.info("Chat messages deleted successfully", chat_id=chat_id)
            return True

        except Exception as e:
            logger.error("Failed to delete chat messages", error=str(e))
            return False

    async def increment_chat_message_count(self, chat_id: str) -> bool:
        """Increment message count for a chat"""
        try:
            table = self.dynamodb.Table(self.get_table_name("chats"))
            table.update_item(
                Key={"chat_id": chat_id},
                UpdateExpression="SET message_count = if_not_exists(message_count, :zero) + :inc",
                ExpressionAttributeValues={":inc": 1, ":zero": 0},
            )
            return True
        except Exception as e:
            logger.error("Failed to increment message count", error=str(e))
            return False

    # Session operations
    async def create_session(
        self, session_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new session"""
        try:
            table_name = self.get_table_name("sessions")
            table = self.dynamodb.Table(table_name)

            session_id = str(uuid4())
            timestamp = datetime.now(timezone.utc)

            session_item = {
                "session_id": session_id,
                "user_id": session_data["user_id"],
                "access_token": session_data["access_token"],
                "refresh_token": session_data["refresh_token"],
                "is_active": True,
                "created_at": timestamp.isoformat(),
                "expires_at": session_data["expires_at"],
                "last_activity": timestamp.isoformat(),
                "device_info": session_data.get("device_info"),
                "ip_address": session_data.get("ip_address"),
            }

            table.put_item(Item=session_item)
            logger.info("Session created successfully", session_id=session_id)
            return session_item

        except Exception as e:
            logger.error("Failed to create session", error=str(e))
            return None

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        try:
            table_name = self.get_table_name("sessions")
            table = self.dynamodb.Table(table_name)

            response = table.get_item(Key={"session_id": session_id})
            return response.get("Item")

        except Exception as e:
            logger.error("Failed to get session", error=str(e))
            return None

    async def update_session(
        self, session_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """Update session"""
        try:
            table_name = self.get_table_name("sessions")
            table = self.dynamodb.Table(table_name)

            # Build update expression
            update_expression = "SET "
            expression_values = {}
            expression_names = {}

            for key, value in update_data.items():
                if value is not None:
                    update_expression += f"#{key} = :{key}, "
                    expression_values[f":{key}"] = value
                    expression_names[f"#{key}"] = key

            # Remove trailing comma
            update_expression = update_expression.rstrip(", ")

            if not expression_values:
                return True

            table.update_item(
                Key={"session_id": session_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
            )

            logger.info("Session updated successfully", session_id=session_id)
            return True

        except Exception as e:
            logger.error("Failed to update session", error=str(e))
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        try:
            table_name = self.get_table_name("sessions")
            table = self.dynamodb.Table(table_name)

            table.delete_item(Key={"session_id": session_id})
            logger.info("Session deleted successfully", session_id=session_id)
            return True

        except Exception as e:
            logger.error("Failed to delete session", error=str(e))
            return False

    async def get_user_sessions(
        self, user_id: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            table_name = self.get_table_name("sessions")
            table = self.dynamodb.Table(table_name)

            # Use GSI to query by user_id
            query_params = {
                "IndexName": "user-sessions-index",
                "KeyConditionExpression": Key("user_id").eq(user_id),
            }

            if active_only:
                query_params["FilterExpression"] = Attr("is_active").eq(True)

            response = table.query(**query_params)
            return response.get("Items", [])

        except Exception as e:
            logger.error("Failed to get user sessions", error=str(e))
            return []

    async def invalidate_user_sessions(self, user_id: str) -> bool:
        """Invalidate all sessions for a user"""
        try:
            sessions = await self.get_user_sessions(user_id, active_only=True)

            for session in sessions:
                await self.update_session(session["session_id"], {"is_active": False})

            logger.info("All user sessions invalidated", user_id=user_id)
            return True

        except Exception as e:
            logger.error("Failed to invalidate user sessions", error=str(e))
            return False

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            table_name = self.get_table_name("sessions")
            table = self.dynamodb.Table(table_name)

            current_time = datetime.now(timezone.utc).isoformat()

            # Scan for expired sessions
            response = table.scan(
                FilterExpression=Attr("expires_at").lt(current_time),
                ProjectionExpression="session_id",
            )

            expired_sessions = response.get("Items", [])
            deleted_count = 0

            for session in expired_sessions:
                if await self.delete_session(session["session_id"]):
                    deleted_count += 1

            logger.info("Expired sessions cleaned up", count=deleted_count)
            return deleted_count

        except Exception as e:
            logger.error("Failed to cleanup expired sessions", error=str(e))
            return 0


# Global instance
dynamodb_service = DynamoDBService()
