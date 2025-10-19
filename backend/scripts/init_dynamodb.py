#!/usr/bin/env python3
"""
Initialize DynamoDB tables for FinanceBot
This script creates all required tables for local development and production
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.dynamodb import dynamodb_service
import structlog

logger = structlog.get_logger(__name__)


async def main():
    """Initialize DynamoDB tables"""
    try:
        logger.info("Starting DynamoDB initialization...")

        # Create tables
        success = await dynamodb_service.create_tables()

        if success:
            logger.info("✅ DynamoDB tables created successfully!")
            logger.info("Tables created:")
            logger.info("- financebot-users")
            logger.info("- financebot-chats")
            logger.info("- financebot-messages")
            logger.info("")
            logger.info("You can now start the FastAPI application.")
        else:
            logger.error("❌ Failed to create DynamoDB tables")
            sys.exit(1)

    except Exception as e:
        logger.error("❌ Error during DynamoDB initialization", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
