from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "SwingTradeApp API",
        "version": "0.1.0",
    }
