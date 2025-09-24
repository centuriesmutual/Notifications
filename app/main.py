"""
Main FastAPI application for the Centuries Mutual Home App
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.routers import clients, messages, documents, webhooks
from app.api.dependencies import get_dropbox_manager, get_amqp_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Centuries Mutual Home App...")
    
    # Test connections
    try:
        dropbox_mgr = get_dropbox_manager()
        if not dropbox_mgr.test_connection():
            logger.error("Failed to connect to Dropbox")
            raise Exception("Dropbox connection failed")
        
        amqp_mgr = get_amqp_manager()
        if not amqp_mgr.is_connected():
            logger.error("Failed to connect to RabbitMQ")
            raise Exception("RabbitMQ connection failed")
        
        logger.info("All connections established successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Centuries Mutual Home App...")
    try:
        amqp_mgr = get_amqp_manager()
        amqp_mgr.disconnect()
        logger.info("Disconnected from RabbitMQ")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise notifications system with Dropbox Advanced and AMQP messaging",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clients.router)
app.include_router(messages.router)
app.include_router(documents.router)
app.include_router(webhooks.router)


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {
        "message": "Centuries Mutual Home App - Enterprise Integration Architecture",
        "version": settings.app_version,
        "status": "operational",
        "components": {
            "dropbox": "connected",
            "rabbitmq": "connected",
            "api": "operational"
        }
    }


@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Dropbox connection
        dropbox_mgr = get_dropbox_manager()
        dropbox_healthy = dropbox_mgr.test_connection()
        
        # Check RabbitMQ connection
        amqp_mgr = get_amqp_manager()
        rabbitmq_healthy = amqp_mgr.is_connected()
        
        overall_health = dropbox_healthy and rabbitmq_healthy
        
        return {
            "status": "healthy" if overall_health else "unhealthy",
            "components": {
                "dropbox": "healthy" if dropbox_healthy else "unhealthy",
                "rabbitmq": "healthy" if rabbitmq_healthy else "unhealthy",
                "api": "healthy"
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
