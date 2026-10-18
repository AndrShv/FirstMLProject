import logging
import time
import functools

logger = logging.getLogger(__name__)


def count_latency(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            logger.info(f"Execution time of {func.__name__}: {duration:.2f} ms")
    return wrapper
