from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.core.settings import settings
from app.services.dynamodb import dynamodb_service
from app.routes import auth, chat


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up FinanceBot API...")

    # Initialize DynamoDB tables
    try:
        success = await dynamodb_service.create_tables()
        if success:
            logger.info("DynamoDB tables initialized successfully")
        else:
            logger.warning("DynamoDB tables may already exist or failed to create")
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB tables: {e}")
        # Don't raise here as tables might already exist
        logger.warning("Continuing startup despite DynamoDB initialization issues")

    yield

    # Shutdown
    logger.info("Shutting down FinanceBot API...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A RAG-based financial assistant API built with FastAPI, OpenAI, and Pinecone",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
)

# Add trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # Configure with your actual domains in production
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


# Root endpoint
@app.get("/")
async def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to FinanceBot API",
        "version": settings.app_version,
        "docs": (
            "/docs" if settings.debug else "Documentation not available in production"
        ),
    }


# Include routers
app.include_router(auth.router)
app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
