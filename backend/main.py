from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.ingest_service.routes import router as ingest_router
from backend.dict_service.routes import router as dict_router
from backend.search_service.routes import router as search_router

from backend.commons.redis_client import close_redis_client, reload_word_frequencies_from_db
from backend.commons.database import get_db


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
    description="API for fetching, searching, and analyzing paragraphs",
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

app.include_router(ingest_router)
app.include_router(search_router)
app.include_router(dict_router)


@app.get("/health")
async def health():
    return {"status": "healthy"}
