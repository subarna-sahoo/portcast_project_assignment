"""
Production-grade monitoring with Prometheus metrics and health checks.
"""
import time
import psutil
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


# Prometheus Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# System Metrics
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage'
)

system_disk_usage = Gauge(
    'system_disk_usage_percent',
    'System disk usage percentage'
)

# Service-specific metrics
database_connections = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

elasticsearch_operations_total = Counter(
    'elasticsearch_operations_total',
    'Total Elasticsearch operations',
    ['operation', 'status']
)

word_frequencies_cache_hits = Counter(
    'word_frequencies_cache_hits_total',
    'Total word frequency cache hits'
)

word_frequencies_cache_misses = Counter(
    'word_frequencies_cache_misses_total',
    'Total word frequency cache misses'
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Track request in progress
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Track request duration
        start_time = time.time()

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            # Track failed requests
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status="500"
            ).inc()
            raise
        finally:
            # Record duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Decrement in-progress
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

        # Track total requests
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()

        return response


def update_system_metrics():
    """Update system resource metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_cpu_usage.set(cpu_percent)

        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)

        # Disk usage
        disk = psutil.disk_usage('/')
        system_disk_usage.set(disk.percent)
    except Exception as e:
        print(f"⚠ Failed to update system metrics: {e}")


async def get_metrics():
    """Generate Prometheus metrics."""
    # Update system metrics before serving
    update_system_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
