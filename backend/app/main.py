import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SwingTradeApp API starting up (env=%s)", settings.APP_ENV)
    yield
    logger.info("SwingTradeApp API shutting down")


app = FastAPI(
    title="SwingTradeApp API",
    description="Market environment suitability engine for swing trading.",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = settings.get_cors_origins()
_allow_credentials = "*" not in _cors_origins  # credentials + wildcard are incompatible

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analysis_router)
