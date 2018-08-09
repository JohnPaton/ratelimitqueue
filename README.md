# RateLimitQueue

A rate limited wrapper for Python's thread safe queues.

Some external APIs have rate limits that allow faster-than-consecutive queries, e.g. if the rate limit is very high or the API response is quite slow. To make the most of the API, the best option is to make API calls from multiple threads. Then you can put the requests or URLs to call in a `queue.Queue` and have the threads consume the URLs as they make the calls. However, you still have to make sure that the total calls from all your threads don't exceed the rate limit. 

The `ratelimitqueue` package extends the three built-in Python from from `queue` module - `Queue`, `LifeQueue`, and `PriorityQueue` - with configurable, rate limited counterparts. Specifically, the `get()` method is rate limited across all threads so that workers can safely consume from the queue in a `while queue.not_empty`, and putting the items in the queue doesn't need to require blocking the main thread.

## Installation

To get started, clone this repository and install it with `pip`:

```bash
git clone git@github.com:JohnPaton/ratelimitqueue.git
pip install ratelimitqueue
```

## Basic Usage

The most basic usage is to rate limit calls in the main thread
