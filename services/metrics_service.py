from prometheus_client import Counter, Histogram, Gauge, Summary, REGISTRY, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator, metrics
import time
from typing import Callable, Any
from functools import wraps
from loguru import logger
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import re

# Define metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['model', 'success']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0, float('inf'))
)

epic_breakdown_duration_seconds = Histogram(
    'epic_breakdown_duration_seconds',
    'Epic breakdown operation duration in seconds',
    ['epic_key'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float('inf'))
)

active_epic_breakdowns = Gauge(
    'active_epic_breakdowns',
    'Number of currently running epic breakdowns'
)

# Add new metrics for endpoint type tracking
endpoint_request_duration_seconds = Histogram(
    'endpoint_request_duration_seconds',
    'Request duration in seconds by endpoint type',
    ['endpoint_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, float('inf'))
)

db_operation_duration_seconds = Histogram(
    'db_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation_type'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, float('inf'))
)

# Add MongoDB import metrics
mongodb_import_duration_seconds = Histogram(
    'mongodb_import_duration_seconds',
    'Time to import breakdown results to MongoDB in seconds',
    ['epic_key'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))
)

mongodb_import_proposal_count = Histogram(
    'mongodb_import_proposal_count',
    'Number of proposals imported to MongoDB per operation',
    ['epic_key'],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, float('inf'))
)

# Create a request timing middleware class
class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure request processing time by endpoint type"""
    
    # Map of URL patterns to endpoint types
    ENDPOINT_PATTERNS = [
        (r'/api/v1/llm/break-down-epic/.*', 'epic_breakdown'),
        (r'/api/v1/llm/create-epic-subtasks/.*', 'epic_breakdown'),
        (r'/api/v1/llm/generate-description/.*', 'ticket_generation'),
        (r'/api/v1/llm/analyze-complexity/.*', 'complexity_analysis'),
        (r'/api/v1/llm/design-architecture/.*', 'architecture_design'),
        (r'/api/v1/llm/revise-plan/.*', 'plan_revision'),
        (r'/api/v1/llm/confirm-revision/.*', 'plan_revision'),
        (r'/api/v1/llm/apply-revision/.*', 'plan_revision'),
        (r'/api/v1/jira/.*', 'jira_operation'),
        (r'/health', 'health_check'),
        (r'/metrics', 'metrics'),
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Determine endpoint type
        endpoint_type = 'other'
        path = request.url.path
        for pattern, ep_type in self.ENDPOINT_PATTERNS:
            if re.match(pattern, path):
                endpoint_type = ep_type
                break
        
        # Record timing metric
        endpoint_request_duration_seconds.labels(endpoint_type=endpoint_type).observe(duration)
        
        # Log for significant durations (over 1 second)
        if duration > 1.0:
            logger.info(f"Request to {path} took {duration:.2f}s (endpoint_type={endpoint_type})")
        
        return response


def setup_metrics(app: FastAPI) -> None:
    """
    Set up Prometheus instrumentation for FastAPI
    
    Args:
        app: FastAPI application instance
    """
    # Add request timing middleware
    app.add_middleware(RequestTimingMiddleware)
    
    # Create instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=[".*admin.*", "/metrics"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    
    # Add additional metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="http",
            metric_subsystem="",
        )
    )
    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="http",
            metric_subsystem="",
        )
    )
    instrumentator.add(
        metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="http",
            metric_subsystem="",
        )
    )
    
    # Instrument app
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=True, tags=["monitoring"])
    
    logger.info("Prometheus metrics instrumentation set up successfully")


# Database operation timing utility
async def track_db_operation(operation_type: str, func: Callable, *args, **kwargs) -> Any:
    """
    Track a database operation with timing metrics
    
    Args:
        operation_type: Type of operation (insert, query, update, etc.)
        func: Async function to call
        args: Args to pass to the function
        kwargs: Kwargs to pass to the function
        
    Returns:
        The result of the function call
    """
    start_time = time.time()
    try:
        result = await func(*args, **kwargs)
        return result
    finally:
        duration = time.time() - start_time
        db_operation_duration_seconds.labels(operation_type=operation_type).observe(duration)
        if duration > 0.5:  # Log slow DB operations (over 500ms)
            logger.debug(f"DB operation {operation_type} completed in {duration:.3f}s")


async def track_llm_request(model: str, func: Callable, *args, **kwargs) -> Any:
    """
    Track an LLM request with timing and success/failure metrics
    
    Args:
        model: LLM model name
        func: Async function to call
        args: Args to pass to the function
        kwargs: Kwargs to pass to the function
        
    Returns:
        The result of the function call
    """
    start_time = time.time()
    success = True
    try:
        result = await func(*args, **kwargs)
        return result
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time
        llm_requests_total.labels(model=model, success=str(success).lower()).inc()
        llm_request_duration_seconds.labels(model=model).observe(duration)
        logger.debug(f"LLM request to {model} completed in {duration:.3f}s (success={success})")


class EpicBreakdownTracker:
    """Context manager to track epic breakdown operations"""
    
    def __init__(self, epic_key: str):
        """Initialize with epic key"""
        self.epic_key = epic_key
        self.start_time = None
    
    async def __aenter__(self):
        """Enter context manager"""
        self.start_time = time.time()
        active_epic_breakdowns.inc()
        logger.debug(f"Starting tracked epic breakdown for {self.epic_key}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        duration = time.time() - self.start_time
        epic_breakdown_duration_seconds.labels(epic_key=self.epic_key).observe(duration)
        active_epic_breakdowns.dec()
        logger.debug(f"Completed epic breakdown for {self.epic_key} in {duration:.3f}s") 