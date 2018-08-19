import time
import queue


def get_time_remaining(start, timeout=None):
    if timeout is None:
        return None
    else:
        time_elapsed = start - time.time()

        return timeout - time_elapsed


def put_time_when_possible(q, timeout=None):
    while True:
        try:
            q.put(time.time(), block=False, timeout=timeout)
            return
        except queue.Full:
            pass
