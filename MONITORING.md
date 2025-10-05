# Monitoring Guide

## 📊 Production-Grade Monitoring Stack

This project includes comprehensive monitoring with:
- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **Health Checks** - Service availability monitoring
- **Structured Logging** - Application logs

---

## 🚀 Access Monitoring Tools

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana Dashboard** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | None |
| **API Health** | http://localhost/api/health | None |
| **API Metrics** | http://localhost/api/metrics | None |

---

## 📈 Available Metrics

### HTTP Metrics

**`http_requests_total`** - Counter
- Total number of HTTP requests
- Labels: `method`, `endpoint`, `status`
```promql
# Request rate per second
rate(http_requests_total[5m])

# Total requests by endpoint
sum by(endpoint) (http_requests_total)
```

**`http_request_duration_seconds`** - Histogram
- Request latency in seconds
- Labels: `method`, `endpoint`
```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

**`http_requests_in_progress`** - Gauge
- Current requests being processed
- Labels: `method`, `endpoint`
```promql
# Current requests in progress
http_requests_in_progress
```

### System Metrics

**`system_cpu_usage_percent`** - Gauge
- CPU usage percentage (0-100)
```promql
system_cpu_usage_percent
```

**`system_memory_usage_percent`** - Gauge
- Memory usage percentage (0-100)
```promql
system_memory_usage_percent
```

**`system_disk_usage_percent`** - Gauge
- Disk usage percentage (0-100)
```promql
system_disk_usage_percent
```

### Service Metrics

**`database_connections_active`** - Gauge
- Number of active database connections
```promql
database_connections_active
```

**`redis_operations_total`** - Counter
- Total Redis operations
- Labels: `operation`, `status`
```promql
rate(redis_operations_total[5m])
```

**`elasticsearch_operations_total`** - Counter
- Total Elasticsearch operations
- Labels: `operation`, `status`
```promql
rate(elasticsearch_operations_total[5m])
```

**`word_frequencies_cache_hits_total`** - Counter
- Cache hit count
```promql
rate(word_frequencies_cache_hits_total[5m])
```

**`word_frequencies_cache_misses_total`** - Counter
- Cache miss count
```promql
rate(word_frequencies_cache_misses_total[5m])
```

---

## 🎯 Grafana Dashboard

The pre-configured dashboard includes:

### 1. Request Rate
- Real-time request rate by endpoint and method
- Shows API traffic patterns

### 2. Request Latency
- p50 and p95 latency percentiles
- Helps identify slow endpoints

### 3. CPU Usage
- Current CPU usage gauge
- Thresholds: Yellow (60%), Red (80%)

### 4. Memory Usage
- Current memory usage gauge
- Thresholds: Yellow (70%), Red (90%)

### 5. Response Status Codes
- Distribution of HTTP status codes
- Helps identify errors

---

## 🏥 Health Checks

### Overall Health
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
      "latency_ms": 2.5,
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.2,
      "message": "Redis connection successful"
    },
    "elasticsearch": {
      "status": "healthy",
      "latency_ms": 5.8,
      "cluster_status": "green",
      "number_of_nodes": 1,
      "message": "Elasticsearch cluster status: green"
    }
  }
}
```

**Status Values:**
- `healthy` - All services operational
- `degraded` - Some services have warnings
- `unhealthy` - Critical services are down

### Liveness Probe (Kubernetes/Docker)
```bash
curl http://localhost/api/health/live
```

Returns `200 OK` if service is running.

### Readiness Probe (Kubernetes/Docker)
```bash
curl http://localhost/api/health/ready
```

Returns:
- `200 OK` - Service ready for traffic
- `503 Service Unavailable` - Service not ready

---

## 🔍 Useful Prometheus Queries

### API Performance

**Error Rate**
```promql
# Percentage of 5xx errors
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

**Request Success Rate**
```promql
# Percentage of successful requests (2xx, 3xx)
sum(rate(http_requests_total{status=~"[23].."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

**Top Slowest Endpoints**
```promql
# Average latency by endpoint
topk(5,
  rate(http_request_duration_seconds_sum[5m]) /
  rate(http_request_duration_seconds_count[5m])
)
```

### System Health

**High CPU Usage Alert**
```promql
system_cpu_usage_percent > 80
```

**High Memory Usage Alert**
```promql
system_memory_usage_percent > 90
```

**High Disk Usage Alert**
```promql
system_disk_usage_percent > 85
```

### Cache Performance

**Cache Hit Rate**
```promql
# Percentage of cache hits
rate(word_frequencies_cache_hits_total[5m]) /
(rate(word_frequencies_cache_hits_total[5m]) + rate(word_frequencies_cache_misses_total[5m])) * 100
```

---

## 📝 Logging

### Log Levels

Logs are configurable via environment variable or code:

```python
from backend.commons.logging_config import setup_logging

# Text logs (default)
setup_logging(log_level="INFO", json_logs=False)

# JSON logs (production)
setup_logging(log_level="INFO", json_logs=True)
```

**Log Levels:**
- `DEBUG` - Detailed information for debugging
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

### Viewing Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
docker-compose logs -f backend
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

**Last 100 lines:**
```bash
docker-compose logs --tail=100 backend
```

---

## 🚨 Alerting (Optional)

### Prometheus Alert Rules

Create `monitoring/alert-rules.yml`:

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "p95 latency is {{ $value }}s"

      - alert: ServiceDown
        expr: up{job="portcast-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "API service is not responding"
```

---

## 📊 Production Recommendations

### 1. Data Retention

Configure Prometheus retention (default: 15 days):
```yaml
# In docker-compose.yml, prometheus command:
- '--storage.tsdb.retention.time=30d'
- '--storage.tsdb.retention.size=50GB'
```

### 2. Grafana Persistence

Grafana data persists in `grafana_data` volume. Backup periodically:
```bash
docker run --rm --volumes-from portcast_grafana -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz /var/lib/grafana
```

### 3. Prometheus Backup

Backup Prometheus data:
```bash
docker run --rm --volumes-from portcast_prometheus -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /prometheus
```

### 4. External Monitoring

For production, consider:
- **Datadog** - Full-stack monitoring
- **New Relic** - APM and infrastructure
- **Sentry** - Error tracking
- **PagerDuty** - On-call alerting

---

## 🔧 Troubleshooting

### Grafana won't start

```bash
# Check logs
docker-compose logs grafana

# Restart
docker-compose restart grafana
```

### Prometheus not scraping metrics

```bash
# Check Prometheus targets
http://localhost:9090/targets

# Verify backend is exposing metrics
curl http://localhost/api/metrics

# Check prometheus.yml configuration
cat monitoring/prometheus.yml
```

### Dashboard not showing data

1. Check Prometheus datasource in Grafana
2. Verify metrics are being collected: http://localhost:9090/graph
3. Check time range in dashboard (default: last 15 minutes)

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FastAPI Instrumentation](https://fastapi.tiangolo.com/)
- [prometheus_client Python](https://github.com/prometheus/client_python)

---

**Monitor your APIs effectively! 📊✨**
