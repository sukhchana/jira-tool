from utils import bootstrap  # This must be the first import
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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
    return {"detail": exc.detail, "status_code": exc.status_code}

if __name__ == "__main__":
    logger.info("Initializing JIRA Ticket Creator API")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
