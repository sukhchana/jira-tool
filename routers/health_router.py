from fastapi import APIRouter

router = APIRouter()

@router.get("/health", summary="Health Check", description="Simple health check endpoint")
async def health_check():
    return "OK" 