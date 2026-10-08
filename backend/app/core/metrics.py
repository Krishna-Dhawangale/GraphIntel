import time
from typing import Optional
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

# 1. Prometheus Metric Instruments
REQUEST_COUNT = Counter(
    "graphintel_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "graphintel_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

RETRIEVAL_LATENCY = Histogram(
    "graphintel_retrieval_latency_seconds",
    "Retrieval duration in seconds",
    ["mode"],  # vector, graph, hybrid
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)

LLM_TOKENS_TOTAL = Counter(
    "graphintel_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],  # type: prompt, completion
)

CACHE_HITS = Counter(
    "graphintel_cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "graphintel_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

DEGRADED_REQUESTS = Counter(
    "graphintel_degraded_requests_total",
    "Total queries operating in degraded fallback mode",
    ["reason"],
)

QUEUE_DEPTH = Gauge(
    "graphintel_worker_queue_depth",
    "Current depth of asynchronous background worker queue",
)


def record_request_metrics(method: str, endpoint: str, status_code: int, duration_sec: float) -> None:
    """Helper to record HTTP request metrics."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration_sec)


def record_retrieval_metrics(mode: str, duration_sec: float) -> None:
    """Helper to record retrieval stage latency."""
    RETRIEVAL_LATENCY.labels(mode=mode).observe(duration_sec)


def record_token_usage(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Helper to record LLM token usage."""
    if prompt_tokens > 0:
        LLM_TOKENS_TOTAL.labels(model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        LLM_TOKENS_TOTAL.labels(model=model, type="completion").inc(completion_tokens)


def record_degraded_event(reason: str) -> None:
    """Helper to record degraded fallback invocation."""
    DEGRADED_REQUESTS.labels(reason=reason).inc()


def get_prometheus_metrics_response() -> Response:
    """Returns the Prometheus formatted metrics response."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
