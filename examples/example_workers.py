"""Example: Make rate limited API calls in worker threads"""

import ratelimitqueue
import multiprocessing.dummy
import time
import random


def make_call_to_slow_api(url):
    time.sleep(random.uniform(1, 2))
    print("Calling:", url)


LIST_OF_URLS = ["https://example.com/{}".format(i) for i in range(25)]

rlq = ratelimitqueue.RateLimitQueue(calls=3, per=2)
stop_flag = multiprocessing.dummy.Event()
n_workers = 4


def worker(rlq):
    """Makes API calls on URLs from queue until it is empty."""
    while rlq.qsize() > 0:
        url = rlq.get()
        make_call_to_slow_api(url)
        rlq.task_done()


# load up the queue
for url in LIST_OF_URLS:
    rlq.put(url)

# make the calls
with multiprocessing.dummy.Pool(n_workers, worker, (rlq,)) as pool:
    rlq.join()
