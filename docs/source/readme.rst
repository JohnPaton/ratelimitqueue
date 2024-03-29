|PyPI version| |Downloads| |Build Status| |Coverage Status|
|Documentation Status| |Code style: black|

🛑 RateLimitQueue
================

A rate limited wrapper for Python’s thread safe queues.

Some external APIs have rate limits that allow faster-than-consecutive
queries, e.g. if the rate limit is very high or the API response is
quite slow. To make the most of the API, the best option is often to
make API calls from multiple threads. Then you can put the requests or
URLs to call in a ``queue.Queue`` and have the threads consume the URLs
as they make the calls. However, you still have to make sure that the
total calls from all your threads don’t exceed the rate limit, which
requires some nontrivial coordination.

The ``ratelimitqueue`` package extends the three built-in Python queues
from from ``queue`` package - ``Queue``, ``LifoQueue``, and
``PriorityQueue`` - with configurable, rate limited counterparts.
Specifically, the ``get()`` method is rate limited across all threads so
that workers can safely consume from the queue in an unlimited loop, and
putting the items in the queue doesn’t need to require blocking the main
thread.

🔌 Installation
--------------

To get started, install ``ratelimitqueue`` with ``pip``:

.. code:: bash

   pip install ratelimitqueue

🌟 Examples
----------

The most basic usage is rate limiting calls in the main thread by
pre-loading a ``RateLimitQueue``. For a rate limit of 2 calls per
second:

.. code:: python

   rlq = ratelimitqueue.RateLimitQueue(calls=2, per=1)

   # load up the queue
   for url in LIST_OF_URLS:
       rlq.put(url)

   # make the calls
   while rlq.qsize() > 0:
       url = rlq.get()
       make_call_to_api(url)
       rlq.task_done()

A more typical use case would be to have a pool of workers making API
calls in parallel:

.. code:: python

   rlq = ratelimitqueue.RateLimitQueue(calls=3, per=2)
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

Working versions of these examples can be found in the `examples
directory <https://github.com/JohnPaton/ratelimitqueue/tree/master/examples>`__.

.. |PyPI version| image:: https://badge.fury.io/py/ratelimitqueue.svg
   :target: https://badge.fury.io/py/ratelimitqueue
.. |Downloads| image:: https://pepy.tech/badge/ratelimitqueue
   :target: https://pepy.tech/project/ratelimitqueue
.. |Build Status| image:: https://travis-ci.com/JohnPaton/ratelimitqueue.svg?branch=master
   :target: https://travis-ci.com/JohnPaton/ratelimitqueue
.. |Coverage Status| image:: https://coveralls.io/repos/github/JohnPaton/ratelimitqueue/badge.svg
   :target: https://coveralls.io/github/JohnPaton/ratelimitqueue
.. |Documentation Status| image:: https://readthedocs.org/projects/ratelimitqueue/badge/?version=latest
   :target: https://ratelimitqueue.readthedocs.io/en/latest/?badge=latest
.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
