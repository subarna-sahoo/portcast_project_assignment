"""
Monitoring and health check endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.commons.database import get_db
from backend.commons.health import (
    get_overall_health,
    get_readiness_check,
    get_liveness_check
)
from backend.commons.monitoring import get_metrics


router = APIRouter(tags=["monitoring"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check endpoint.
    Returns health status of all services with latency metrics.
    """
    return await get_overall_health(db)


@router.get("/health/live")
async def liveness():
    """
    Liveness probe for Kubernetes/Docker.
    Returns 200 if service is running.
    """
    return await get_liveness_check()


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe for Kubernetes/Docker.
    Returns 200 if service is ready to accept traffic, 503 otherwise.
    """
    return await get_readiness_check(db)


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus format.
    """
    return await get_metrics()
