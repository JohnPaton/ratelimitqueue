|Build Status| |Coverage Status| |Documentation Status| |Code style:
black|

RateLimitQueue
==============

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
from from ``queue`` package - ``Queue``, ``LifeQueue``, and
``PriorityQueue`` - with configurable, rate limited counterparts.
Specifically, the ``get()`` method is rate limited across all threads so
that workers can safely consume from the queue in an unlimited loop, and
putting the items in the queue doesn’t need to require blocking the main
thread.

.. contents::

.. toctree::
   :hidden:

   index

.. toctree::
   :caption: API Documentation

   ratelimitqueue

Installation
------------

To install ``ratelimitqueue``, clone the repository and install with
``pip``:

.. code:: bash

   $ git clone https://github.com/JohnPaton/ratelimitqueue.git
   $ cd ratelimitqueue
   $ pip install .




.. |Build Status| image:: https://travis-ci.com/JohnPaton/ratelimitqueue.svg?branch=master
   :target: https://travis-ci.com/JohnPaton/ratelimitqueue
.. |Coverage Status| image:: https://coveralls.io/repos/github/JohnPaton/ratelimitqueue/badge.svg
   :target: https://coveralls.io/github/JohnPaton/ratelimitqueue
.. |Documentation Status| image:: https://readthedocs.org/projects/ratelimitqueue/badge/?version=latest
   :target: https://ratelimitqueue.readthedocs.io/en/latest/?badge=latest
.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black