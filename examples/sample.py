import time
from functools import wraps


def retry(times=3, delay=0.5):
    """Retry a flaky function with a fixed delay."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == times:
                        raise
                    print(f"attempt {attempt} failed: {exc}")
                    time.sleep(delay)

        return wrapper

    return decorator
