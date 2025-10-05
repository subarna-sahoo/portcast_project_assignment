"""
Health check endpoints for monitoring service availability.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.commons.redis_client import get_redis_client
from backend.commons.elasticsearch_client import ElasticsearchClient


class HealthStatus:
    """Health check status codes."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


async def check_database_health(db: AsyncSession) -> Dict[str, Any]:
    """Check PostgreSQL database health."""
    try:
        start_time = datetime.now()
        # Simple query to test connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency_ms, 2),
            "message": "Database connection successful"
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "message": "Database connection failed"
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis health."""
    try:
        redis_client = await get_redis_client()
        start_time = datetime.now()

        # Test Redis connection with PING
        await redis_client.ping()

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(latency_ms, 2),
            "message": "Redis connection successful"
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "message": "Redis connection failed"
        }


async def check_elasticsearch_health() -> Dict[str, Any]:
    """Check Elasticsearch health."""
    try:
        start_time = datetime.now()

        # Test Elasticsearch connection
        es_client = ElasticsearchClient.get_client()
        health = await es_client.cluster.health()

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        status = health.get("status", "unknown")
        es_status = HealthStatus.HEALTHY if status == "green" else HealthStatus.DEGRADED

        return {
            "status": es_status,
            "latency_ms": round(latency_ms, 2),
            "cluster_status": status,
            "number_of_nodes": health.get("number_of_nodes", 0),
            "message": f"Elasticsearch cluster status: {status}"
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "message": "Elasticsearch connection failed"
        }


async def get_overall_health(db: AsyncSession) -> Dict[str, Any]:
    """Get overall health status of all services."""
    # Run all health checks concurrently
    db_health, redis_health, es_health = await asyncio.gather(
        check_database_health(db),
        check_redis_health(),
        check_elasticsearch_health(),
        return_exceptions=True
    )

    # Handle any exceptions from gather
    if isinstance(db_health, Exception):
        db_health = {"status": HealthStatus.UNHEALTHY, "error": str(db_health)}
    if isinstance(redis_health, Exception):
        redis_health = {"status": HealthStatus.UNHEALTHY, "error": str(redis_health)}
    if isinstance(es_health, Exception):
        es_health = {"status": HealthStatus.UNHEALTHY, "error": str(es_health)}

    # Determine overall status
    all_healthy = all(
        check.get("status") == HealthStatus.HEALTHY
        for check in [db_health, redis_health, es_health]
    )

    any_unhealthy = any(
        check.get("status") == HealthStatus.UNHEALTHY
        for check in [db_health, redis_health, es_health]
    )

    if all_healthy:
        overall_status = HealthStatus.HEALTHY
    elif any_unhealthy:
        overall_status = HealthStatus.UNHEALTHY
    else:
        overall_status = HealthStatus.DEGRADED

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_health,
            "redis": redis_health,
            "elasticsearch": es_health
        }
    }


async def get_readiness_check(db: AsyncSession) -> Dict[str, Any]:
    """
    Readiness check - determines if service is ready to accept traffic.
    Returns 200 if all critical services are healthy, 503 otherwise.
    """
    health = await get_overall_health(db)

    if health["status"] == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=health)

    return health


async def get_liveness_check() -> Dict[str, Any]:
    """
    Liveness check - determines if service is running.
    Simple check that doesn't depend on external services.
    """
    return {
        "status": HealthStatus.HEALTHY,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Service is alive"
    }
