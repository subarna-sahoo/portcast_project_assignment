# Portcast Project Assignment

> **Production-grade FastAPI application** for fetching, searching, and analyzing paragraphs with full-text search, word frequency analysis, and comprehensive monitoring.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Monitoring & Health](#monitoring--health)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Development](#development)
- [Deployment](#deployment)

---

## 🎯 Overview

This application provides a robust API for:
- **Fetching** paragraphs from external sources (Metaphorpsum API)
- **Searching** paragraphs with fuzzy matching and boolean operators
- **Analyzing** word frequencies with intelligent caching
- **Monitoring** system health and performance metrics

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI 0.115.0 | Async web framework |
| **Database** | PostgreSQL + asyncpg | Primary data store |
| **Search** | Elasticsearch 8.11.0 | Full-text search engine |
| **Cache** | Redis 6.4.0 | Fast data caching |
| **Monitoring** | Prometheus + psutil | Metrics & health checks |
| **Testing** | pytest + pytest-asyncio | Test framework |
| **Proxy** | Nginx | Reverse proxy |
| **Frontend** | React | Simple UI interface |

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Nginx     │─────▶│   FastAPI    │─────▶│ PostgreSQL  │
│   (Proxy)   │      │   Backend    │      │  (Database) │
└─────────────┘      └──────┬───────┘      └─────────────┘
                            │
                    ┌───────┼───────┐
                    ▼       ▼       ▼
              ┌──────┐ ┌──────┐ ┌──────────────┐
              │Redis │ │  ES  │ │ Prometheus   │
              │Cache │ │Search│ │ (Metrics)    │
              └──────┘ └──────┘ └──────────────┘
```

### Data Flow

1. **Ingest**: Metaphorpsum → FastAPI → PostgreSQL + Elasticsearch + Redis
2. **Search**: Client → FastAPI → Elasticsearch → PostgreSQL
3. **Dictionary**: Client → FastAPI → Redis/DB → Dictionary API

---

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Git

### One-Command Setup

```bash
# Clone the repository
git clone <repository-url>
cd portcast_project_assignment

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **API Documentation** | http://localhost/api/docs | Interactive Swagger UI |
| **API Root** | http://localhost/api/ | API endpoints listing |
| **Health Check** | http://localhost/api/health | Service health status |
| **Metrics** | http://localhost/api/metrics | Prometheus metrics |
| **Grafana Dashboard** | http://localhost:3000 | Monitoring dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics storage & queries |
| **Frontend** | http://localhost/ | React UI |

---

## 📚 API Documentation

### Base URL
```
http://localhost/api
```

### Endpoints

#### 1. Fetch Paragraph (`POST /fetch`)

Fetch a new paragraph from Metaphorpsum API and store it.

**Request:**
```bash
curl -X POST http://localhost/api/fetch
```

**Response:**
```json
{
  "id": 1,
  "content": "Lorem ipsum dolor sit amet...",
  "created_at": "2025-10-05T12:00:00Z"
}
```

**Features:**
- Automatically indexes in Elasticsearch
- Updates word frequency counts
- Filters stopwords and short words (< 4 chars)
- Invalidates and updates Redis cache

---

#### 2. Search Paragraphs (`POST /search`)

Search paragraphs with fuzzy matching and boolean operators.

**Request:**
```bash
curl -X POST http://localhost/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "words": ["python", "programming"],
    "operator": "and"
  }'
```

**Parameters:**
- `words` (array): List of search terms
- `operator` (string): `"and"` or `"or"`

**Response:**
```json
{
  "paragraphs": [
    {
      "id": 1,
      "content": "Python programming is awesome...",
      "created_at": "2025-10-05T12:00:00Z"
    }
  ],
  "total": 1
}
```

**Features:**
- Fuzzy matching (fuzziness=2) for typo tolerance
- Maintains Elasticsearch ranking order
- Returns top 10 results

---

#### 3. Get Dictionary (`GET /dictionary`)

Get top 10 most frequent words with definitions.

**Request:**
```bash
curl http://localhost/api/dictionary
```

**Response:**
```json
{
  "definitions": [
    {
      "word": "python",
      "definition": "A high-level programming language",
      "frequency": 150
    }
  ]
}
```

**Features:**
- Redis cache for word frequencies (TTL: 300s)
- External Dictionary API integration
- Definition caching (TTL: 3600s)
- Automatic DB fallback on cache miss

---

### Monitoring Endpoints

#### Health Check (`GET /health`)

Comprehensive health check with latency metrics.

```bash
curl http://localhost/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-05T12:00:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "latency_ms": 2.5
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.2
    },
    "elasticsearch": {
      "status": "healthy",
      "latency_ms": 5.8,
      "cluster_status": "green"
    }
  }
}
```

---

#### Liveness Probe (`GET /health/live`)

Simple liveness check for Kubernetes/Docker.

```bash
curl http://localhost/api/health/live
```

---

#### Readiness Probe (`GET /health/ready`)

Readiness check - returns 503 if services are unhealthy.

```bash
curl http://localhost/api/health/ready
```

---

#### Prometheus Metrics (`GET /metrics`)

Metrics in Prometheus format.

```bash
curl http://localhost/api/metrics
```

**Available Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_in_progress` - Current requests in progress
- `system_cpu_usage_percent` - System CPU usage
- `system_memory_usage_percent` - System memory usage
- `system_disk_usage_percent` - System disk usage

---

## 🧪 Testing

### Test Suite

- **Total Tests**: 33
- **Pass Rate**: 85% (28 passed)
- **Code Coverage**: 71%

### Run Tests

```bash
# Install test dependencies
pip install -r backend/requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific API tests
pytest tests/test_dictionary_api.py -v
pytest tests/test_search_api.py -v
pytest tests/test_ingest_api.py -v
```

### Test Documentation

See [TEST_RESULTS.md](TEST_RESULTS.md) for detailed test results and [tests/README.md](tests/README.md) for testing guide.

---

## 📁 Project Structure

```
portcast_project_assignment/
├── backend/                      # Backend application
│   ├── commons/                  # Shared utilities
│   │   ├── configs.py           # Configuration management
│   │   ├── database.py          # Database connection
│   │   ├── elasticsearch_client.py  # ES client
│   │   ├── redis_client.py      # Redis client
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── monitoring.py        # Prometheus metrics
│   │   ├── health.py            # Health checks
│   │   └── logging_config.py    # Logging setup
│   ├── dict_service/            # Dictionary API service
│   │   ├── routes.py            # API routes
│   │   └── service.py           # Business logic
│   ├── search_service/          # Search API service
│   │   ├── routes.py            # API routes
│   │   └── service.py           # Business logic
│   ├── ingest_service/          # Ingest API service
│   │   ├── routes.py            # API routes
│   │   └── service.py           # Business logic
│   ├── monitoring/              # Monitoring endpoints
│   │   └── routes.py            # Health & metrics routes
│   ├── main.py                  # Application entry point
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Backend container
├── frontend/                     # React frontend
│   ├── public/                  # Static assets
│   └── src/                     # Source code
├── nginx/                        # Nginx configuration
│   ├── nginx.conf               # Nginx config
│   └── Dockerfile               # Nginx container
├── alembic/                      # Database migrations
│   └── versions/                # Migration files
├── tests/                        # Test suite
│   ├── conftest.py              # Test fixtures
│   ├── test_dictionary_api.py   # Dictionary tests
│   ├── test_search_api.py       # Search tests
│   ├── test_ingest_api.py       # Ingest tests
│   └── README.md                # Testing guide
├── docker-compose.yml            # Docker composition
├── alembic.ini                   # Alembic configuration
├── .env                          # Environment variables
├── pytest.ini                    # Pytest configuration
├── README.md                     # This file
└── TEST_RESULTS.md              # Test results
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/portcast_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Elasticsearch
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200

# External APIs
METAPHORPSUM_URL=http://metaphorpsum.com/paragraphs/1/1
DICTIONARY_API_URL=https://api.dictionaryapi.dev/api/v2/entries/en

# Cache Settings
REDIS_WORD_FREQ_TTL=300        # Word frequency cache TTL (seconds)
REDIS_DEFINITION_TTL=3600      # Definition cache TTL (seconds)
TOP_N_CACHED_WORDS=100         # Number of words to cache
```

---

## 💻 Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start services (PostgreSQL, Redis, Elasticsearch)
docker-compose up -d postgres redis elasticsearch

# Run database migrations
alembic upgrade head

# Start development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=backend --cov-report=html

# Format code (optional)
black backend/
isort backend/
```

---

## 🐳 Deployment

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Production Checklist

- [ ] Set strong passwords in `.env`
- [ ] Configure CORS for specific origins
- [ ] Enable HTTPS with SSL certificates
- [ ] Set up Prometheus monitoring
- [ ] Configure log aggregation (e.g., ELK stack)
- [ ] Set up automated backups for PostgreSQL
- [ ] Configure rate limiting
- [ ] Enable API authentication/authorization
- [ ] Set up CI/CD pipeline
- [ ] Configure container health checks

### Kubernetes Deployment

The application includes health check endpoints for Kubernetes:

```yaml
livenessProbe:
  httpGet:
    path: /api/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## 📊 Monitoring

### Prometheus Integration

Scrape configuration for Prometheus:

```yaml
scrape_configs:
  - job_name: 'portcast-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 15s
```

### Grafana Dashboards

Monitor these key metrics:
- Request rate and latency
- Error rates by endpoint
- Database connection pool
- Redis cache hit rate
- Elasticsearch query performance
- System resources (CPU, memory, disk)

---

## 🔗 Important Links

| Resource | Link |
|----------|------|
| **API Swagger Docs** | http://localhost/api/docs |
| **API ReDoc** | http://localhost/api/redoc |
| **Health Check** | http://localhost/api/health |
| **Prometheus Metrics** | http://localhost/api/metrics |
| **Grafana Dashboard** | http://localhost:3000 |
| **Prometheus UI** | http://localhost:9090 |
| **Monitoring Guide** | [MONITORING.md](MONITORING.md) |
| **Test Results** | [TEST_RESULTS.md](TEST_RESULTS.md) |
| **Testing Guide** | [tests/README.md](tests/README.md) |
| **License** | [LICENSE](LICENSE) |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

[⬆ Back to Top](#portcast-project-assignment)

</div>
