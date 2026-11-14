
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from time import perf_counter
from uuid import uuid4


# Current request and nested span context
trace_id_var = ContextVar("trace_id", default="-")
span_stack_var = ContextVar("span_stack", default=())


class TraceContextFilter(logging.Filter):
    """Automatically attach trace and span IDs to log records."""

    def filter(self, record):
        record.trace_id = trace_id_var.get()

        span_stack = span_stack_var.get()
        record.span_id = span_stack[-1] if span_stack else "-"

        return True


# Logger setup
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "agent.log"

logger = logging.getLogger("shopping_assistant")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | "
        "trace_id=%(trace_id)s | span_id=%(span_id)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


if not any(isinstance(f, TraceContextFilter) for f in logger.filters):
    logger.addFilter(TraceContextFilter())


@contextmanager
def trace_context():
    """Create an independent trace for one user request."""

    trace_id = uuid4().hex

    trace_token = trace_id_var.set(trace_id)
    span_token = span_stack_var.set(())

    try:
        yield trace_id

    finally:
        span_stack_var.reset(span_token)
        trace_id_var.reset(trace_token)


@contextmanager
def trace_span(span_name: str):
    """Measure one operation and connect it to its parent span."""

    span_id = uuid4().hex
    parent_stack = span_stack_var.get()

    parent_span_id = (
        parent_stack[-1] if parent_stack else "-"
    )

    span_token = span_stack_var.set(
        parent_stack + (span_id,)
    )

    start_time = perf_counter()

    logger.info(
        "Span started | span_name=%s | parent_span_id=%s",
        span_name,
        parent_span_id
    )

    try:
        yield span_id

    except Exception as error:
        duration = perf_counter() - start_time

        logger.error(
            "Span failed | span_name=%s | duration_seconds=%.3f | error_type=%s",
            span_name,
            duration,
            type(error).__name__
        )
        raise

    else:
        duration = perf_counter() - start_time

        logger.info(
            "Span completed | span_name=%s | duration_seconds=%.3f",
            span_name,
            duration
        )

    finally:
        span_stack_var.reset(span_token)


def traced(span_name: str):
    """Decorator for tracing complete function execution."""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            with trace_span(span_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
