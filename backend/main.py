from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.ingest_service.routes import router as ingest_router
from backend.dict_service.routes import router as dict_router
from backend.search_service.routes import router as search_router
from backend.monitoring.routes import router as monitoring_router

from backend.commons.redis_client import close_redis_client, reload_word_frequencies_from_db
from backend.commons.database import get_db
from backend.commons.monitoring import PrometheusMiddleware
from backend.commons.logging_config import setup_logging
from backend.commons.configs import get_settings

# Setup logging
setup_logging(log_level="INFO", json_logs=False)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Reload Redis cache from DB
    async for db in get_db():
        await reload_word_frequencies_from_db(db)
        break  # Only need one iteration
    yield
    # Shutdown
    await close_redis_client()

app = FastAPI(
    title="Portcast Assignment API",
    description="API for fetching, searching, and analyzing paragraphs with monitoring",
    version="1.0.0",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus monitoring middleware
app.add_middleware(PrometheusMiddleware)

# Include routers
app.include_router(monitoring_router)  # Monitoring endpoints first
app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(dict_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Portcast Assignment API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health",
            "metrics": "/api/metrics",
            "dictionary": "/api/dictionary",
            "search": "/api/search",
            "fetch": "/api/fetch"
        }
    }
