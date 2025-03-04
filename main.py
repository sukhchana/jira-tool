from contextlib import asynccontextmanager
import multiprocessing
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import jira_router, llm_router
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events for the FastAPI application
    """
    # Startup
    logger.info("Starting JIRA Ticket Creator API")
    yield
    # Shutdown
    logger.info("Shutting down JIRA Ticket Creator API")


app = FastAPI(
    title="JIRA Ticket Creator API",
    description="API for creating and managing JIRA tickets with LLM support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    jira_router.router,
    prefix="/api/v1",
    tags=["jira"]
)
app.include_router(
    llm_router.router,
    prefix="/api/v1/llm",
    tags=["llm"]
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP error occurred: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


def calculate_workers():
    """Calculate the optimal number of workers based on CPU count."""
    cpu_count = multiprocessing.cpu_count()
    workers_per_core = int(os.getenv("WORKERS_PER_CORE", "2"))
    workers = (workers_per_core * cpu_count) + 1
    
    # Allow override via environment variable
    return int(os.getenv("WORKERS", workers))


if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = calculate_workers()  # Use the calculate_workers function
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "debug").lower()
    
    # Use environment variable to determine if we should use multiple workers
    if workers > 1:
        logger.info(f"Starting with {workers} workers")
    else:
        logger.info(f"Starting with single worker")
        
    if reload:
        logger.info("Auto-reload enabled")
    
    # Start Uvicorn with the specified settings
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level=log_level
    )
