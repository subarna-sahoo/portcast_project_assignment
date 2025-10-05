# API Test Suite

Comprehensive test suite for the three main APIs in the Portcast assignment project.

## Test Files

1. **test_dictionary_api.py** - Tests for `/dictionary` endpoint
2. **test_search_api.py** - Tests for `/search` endpoint
3. **test_ingest_api.py** - Tests for `/fetch` endpoint

## Test Coverage

### Dictionary API (`/dictionary`)
- ✅ Success with cached data
- ✅ Success from database when cache misses
- ✅ External API failure handling
- ✅ No words in database scenario
- ✅ Redis failure fallback to DB
- ✅ Definition caching
- ✅ Malformed API response handling
- ✅ Top 10 limit enforcement
- ✅ Bytes decoding from Redis

### Search API (`/search`)
- ✅ AND operator search
- ✅ OR operator search
- ✅ No results scenario
- ✅ Single word search
- ✅ Invalid operator validation
- ✅ Empty words list
- ✅ Elasticsearch failure handling
- ✅ Ranking order maintenance
- ✅ Fuzziness application
- ✅ Response schema validation
- ✅ Missing required fields
- ✅ Result limit (10 items)

### Ingest API (`/fetch`)
- ✅ Successful paragraph fetch and storage
- ✅ Word frequency updates
- ✅ Elasticsearch indexing
- ✅ External API failure
- ✅ Elasticsearch failure handling
- ✅ Stopwords filtering
- ✅ Short words filtering (< 4 chars)
- ✅ Existing word frequency incrementation
- ✅ Redis cache updates
- ✅ Redis failure handling
- ✅ Response schema validation
- ✅ Empty content handling

## Setup

1. Install testing dependencies:
```bash
pip install -r backend/requirements.txt
```

2. Ensure you have the necessary environment variables set (see `.env` file)

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_dictionary_api.py
pytest tests/test_search_api.py
pytest tests/test_ingest_api.py
```

### Run specific test
```bash
pytest tests/test_dictionary_api.py::TestDictionaryAPI::test_get_dictionary_success_with_cache
```

### Run with coverage report
```bash
pytest --cov=backend --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`

### Run with verbose output
```bash
pytest -v
```

### Run and show print statements
```bash
pytest -s
```

## Test Structure

All tests use:
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **AsyncClient** - FastAPI test client
- **AsyncMock** - Mocking async operations
- **SQLite in-memory database** - Isolated test database
- **Mock Redis client** - Mocked Redis operations
- **Mocked external services** - Elasticsearch, Dictionary API, Metaphorpsum API

## Key Features

- **Isolated tests**: Each test uses a fresh in-memory SQLite database
- **Mocked dependencies**: All external services (Redis, Elasticsearch, HTTP APIs) are mocked
- **Async support**: Full async/await test support
- **Comprehensive coverage**: Success, failure, edge cases, and error scenarios
- **Fast execution**: No real external dependencies needed

## Notes

- Tests use in-memory SQLite database, so no PostgreSQL required
- All external HTTP calls are mocked
- Redis and Elasticsearch are mocked for isolated testing
- Tests can run in any order (no dependencies between tests)
