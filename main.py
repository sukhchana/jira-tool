from contextlib import asynccontextmanager
import multiprocessing
import os
import time
from starlette.middleware.base import BaseHTTPMiddleware

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from routers import jira_router, llm_router, health_router
from services.metrics_service import setup_metrics
from utils.logger import logger


# Middleware for logging slow requests
class SlowRequestMiddleware(BaseHTTPMiddleware):
    """Middleware to log slow requests"""
    
    def __init__(self, app, threshold_seconds=5.0):
        super().__init__(app)
        self.threshold = threshold_seconds
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        request_time = time.time() - start_time
        
        if request_time > self.threshold:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.url.path} "
                f"took {request_time:.2f}s (threshold: {self.threshold}s)"
            )
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events for the FastAPI application
    """
    # Startup
    logger.info("Starting JIRA Ticket Creator API")
    
    # Create static directory if it doesn't exist
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Check if mermaid_viewer.html exists in the static directory
    viewer_path = static_dir / "mermaid_viewer.html"
    if not viewer_path.exists():
        logger.error(f"Mermaid viewer file not found at {viewer_path}. Please ensure the file exists in the static directory.")
    
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

# Add middleware for monitoring slow requests (threshold: 5 seconds)
app.add_middleware(SlowRequestMiddleware, threshold_seconds=5.0)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up Prometheus metrics
setup_metrics(app)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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
app.include_router(
    health_router.router,
    tags=["monitoring"]
)

# Add a route for the mermaid viewer
@app.get("/mermaid-viewer", description="Mermaid diagram viewer")
async def get_mermaid_viewer():
    return FileResponse("static/mermaid_viewer.html")


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
