from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from routers import jira_router, llm_router
from utils.logger import logger


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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


if __name__ == "__main__":
    logger.info("Initializing JIRA Ticket Creator API")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
