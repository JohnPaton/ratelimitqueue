"""Example: Make rate limited API calls in the main thread."""

import ratelimitqueue


def make_call_to_api(url):
    print("Calling:", url)


LIST_OF_URLS = ["https://example.com/{}".format(i) for i in range(25)]

rlq = ratelimitqueue.RateLimitQueue(calls=2, per=1)

# load up the queue
for url in LIST_OF_URLS:
    rlq.put(url)

# make the calls
while rlq.qsize() > 0:
    url = rlq.get()
    make_call_to_api(url)
    rlq.task_done()
