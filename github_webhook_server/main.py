"""
Main application file for the GitHub Webhook Server.
"""
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from webhook.api import client_router, system_router, webhook_router
from webhook.config import (
    API_DESCRIPTION,
    API_PREFIX,
    API_TITLE,
    API_VERSION,
    CORS_ORIGINS,
    DATA_DIR,
    ENABLE_CORS,
    HOST,
    LOG_FILE,
    LOG_LEVEL,
    LOG_RETENTION,
    LOG_ROTATION,
    PORT,
    RATE_LIMIT,
    RATE_LIMIT_ENABLED,
)
from webhook.models import create_tables
from webhook.schemas import ErrorResponse

# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

# Setup CORS if enabled
if ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup rate limiting if enabled
if RATE_LIMIT_ENABLED:
    import slowapi
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import RateLimitMiddleware
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{RATE_LIMIT}/minute"])
    app.state.limiter = limiter
    app.add_middleware(RateLimitMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        """Handle rate limit exceeded exceptions."""
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                status="error",
                message="Rate limit exceeded",
                detail=str(exc),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            ).dict(),
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            status="error",
            message="Internal server error",
            detail=str(exc),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        ).dict(),
    )

# Include routers
app.include_router(webhook_router, prefix=API_PREFIX)
app.include_router(client_router, prefix=API_PREFIX)
app.include_router(system_router, prefix=API_PREFIX)

# Add a root redirect to the API documentation
@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redirect to the API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

# Setup logging
def setup_logging():
    """Configure logging for the application."""
    # Ensure log directory exists
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(exist_ok=True)

    # Configure loguru
    logger.remove()  # Remove default handler
    logger.add(
        LOG_FILE,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        level=LOG_LEVEL.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    logger.add(
        lambda msg: print(msg),
        level=LOG_LEVEL.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    logger.info(f"Logging configured. Log file: {LOG_FILE}")

# Initialize the application
def init_app():
    """Initialize the application."""
    # Setup logging
    setup_logging()

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    logger.info(f"Data directory: {DATA_DIR}")

    # Create database tables
    create_tables()
    logger.info("Database tables created")

    logger.info(f"Server initialized. API version: {API_VERSION}")

# Run the application
def run_app():
    """Run the application."""
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL.lower(),
        reload=True,
    )

if __name__ == "__main__":
    init_app()
    run_app()