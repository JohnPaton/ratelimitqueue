import time
import queue


def get_time_remaining(start, timeout=None):
    if timeout is None:
        return None
    else:
        time_elapsed = start - time.time()

        return timeout - time_elapsed
