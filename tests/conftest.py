import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Import models FIRST so they are registered with Base metadata
from backend.commons.models import Paragraph, WordFrequency
from backend.commons.database import get_db, Base
from backend.main import app
from backend.commons.redis_client import get_redis_client


# Test database URL - using file-based SQLite for tests to avoid in-memory issues
import tempfile
import os

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine"""
    # Remove test db if exists
    if os.path.exists("./test.db"):
        os.remove("./test.db")

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine):
    """Create a test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        # Rollback after test
        await session.rollback()


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zrevrange = AsyncMock(return_value=[])
    redis_mock.zrem = AsyncMock(return_value=1)
    return redis_mock


@pytest_asyncio.fixture
async def client(test_db, mock_redis):
    """Create a test HTTP client with database and redis overrides"""

    async def override_get_db():
        yield test_db

    async def override_get_redis():
        return mock_redis

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    # Create client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_paragraph_data():
    """Sample paragraph data for testing"""
    return {
        "id": 1,
        "content": "This is a test paragraph with some sample words.",
        "created_at": datetime.now()
    }


@pytest.fixture
def sample_word_frequencies():
    """Sample word frequency data for testing"""
    return [
        ("test", 100),
        ("sample", 80),
        ("paragraph", 60),
        ("words", 50),
        ("data", 40),
        ("python", 30),
        ("fastapi", 25),
        ("redis", 20),
        ("database", 15),
        ("search", 10)
    ]
