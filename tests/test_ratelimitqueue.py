"""Tests for ratelimitqueue/ratelimitqueue.py"""
import pytest
from unittest import mock
from .utils import almost

from ratelimitqueue.ratelimitqueue import RateLimitQueue, RateLimitException
from ratelimitqueue.ratelimitqueue import RateLimitLifoQueue
from ratelimitqueue.ratelimitqueue import RateLimitPriorityQueue

from queue import Empty

import time
import random

# take randomness out of fuzzing
random.uniform = mock.Mock(side_effect=lambda a, b: a + (b - a) / 2)


class GetMixinTester:
    # tests of __init__()
    def test_no_per(self):
        rlq = self.QueueClass()
        del rlq.per
        rlq.put(1)
        with pytest.raises(AttributeError):
            rlq.get()

    def test_no_fuzz(self):
        rlq = self.QueueClass()
        del rlq.fuzz
        rlq.put(1)
        with pytest.raises(AttributeError):
            rlq.get()

    def test_no__call_log(self):
        rlq = self.QueueClass()
        del rlq._call_log
        rlq.put(1)
        with pytest.raises(AttributeError):
            rlq.get()

    def test_maxsize(self):
        rlq = self.QueueClass(0)
        assert rlq.maxsize == 0

        rlq = self.QueueClass(3)
        assert rlq.maxsize == 3

    def test_calls_not_less_than_1(self):
        with pytest.raises(ValueError):
            rlq = self.QueueClass(1, 0, 10)

        with pytest.raises(ValueError):
            rlq = self.QueueClass(1, -1, 10)

    # tests of get()

    def test_timeout_not_less_than_0(self):
        rlq = self.QueueClass()
        rlq.put(1)
        with pytest.raises(ValueError):
            rlq.get(timeout=-1)

    def test_item_in_queue(self):
        rlq = self.QueueClass()
        rlq.put(1)
        assert rlq.get() == 1

    def test_first_put_fast(self):
        rlq = self.QueueClass()
        start = time.time()
        rlq.put(1)
        rlq.get()

        assert almost(0, time.time() - start)

    def test_default_rate_limit(self):
        rlq = self.QueueClass()
        start = time.time()

        rlq.put(1)
        rlq.put(1)
        rlq.get()
        rlq.get()

        assert almost(1, time.time() - start)

    def test_rate_limit_calls(self):
        rlq = self.QueueClass(calls=2)
        start = time.time()

        rlq.put(1)
        rlq.put(1)
        rlq.put(1)
        rlq.put(1)

        rlq.get()
        rlq.get()
        rlq.get()
        assert almost(1, time.time() - start)

        rlq.get()
        assert almost(1, time.time() - start)

    def test_rate_limit_per(self):
        rlq = self.QueueClass(per=0.5)
        start = time.time()

        rlq.put(1)
        rlq.put(1)
        rlq.put(1)

        rlq.get()
        rlq.get()
        rlq.get()

        assert almost(1, time.time() - start)

    def test_rate_limit_calls_per(self):
        rlq = self.QueueClass(calls=2, per=0.5)
        start = time.time()

        rlq.put(1)
        rlq.put(1)
        rlq.put(1)
        rlq.put(1)

        rlq.get()
        rlq.get()
        rlq.get()
        assert almost(0.5, time.time() - start)

        rlq.get()
        assert almost(0.5, time.time() - start)

    def test_not_block_raises_rate_limit(self):
        rlq = self.QueueClass(calls=1, per=3)
        rlq.put(1)
        rlq.put(1)

        rlq.get()

        with pytest.raises(RateLimitException):
            rlq.get(block=False)

    def test_not_block_raises_empty(self):
        rlq = self.QueueClass(calls=1, per=0)

        with pytest.raises(Empty):
            rlq.get(block=False)

    def test_timeout_on_rate_limit_raises_rate_limit(self):
        rlq = self.QueueClass(per=10)
        rlq.put(1)
        rlq.put(1)

        rlq.get()
        with pytest.raises(RateLimitException):
            rlq.get(timeout=1)

    def test_timeout_on_queue_size_raises_empty(self):
        rlq = self.QueueClass(maxsize=1, per=0)

        with pytest.raises(Empty):
            rlq.get(timeout=0.001)

    def test_timeout_on_queue_size_timing(self):
        rlq = self.QueueClass(maxsize=1, per=0)

        with pytest.raises(Empty):
            start = time.time()
            rlq.get(timeout=0.5)

        assert almost(0.5, time.time() - start)

    def test_no_fuzz_when_at_rate_limit(self):
        rlq = self.QueueClass(per=0.5)
        rlq.put(1)
        rlq.get()

        rlq.fuzz = 1000

        start = time.time()
        rlq.put(1)
        rlq.get()

        assert almost(0.5, time.time() - start)

    def test_fuzz(self):
        rlq = self.QueueClass(per=0.5, fuzz=1)
        start = time.time()
        rlq.put(1)
        rlq.get()

        end = time.time()

        assert almost(0.5, end - start)

    def test_fuzz_less_than_timeout(self):
        rlq = self.QueueClass(fuzz=10000)
        start = time.time()
        rlq.put(1)
        rlq.get(timeout=0.5)
        end = time.time()
        elapsed = end - start
        assert almost(0.5, elapsed)


class TestRateLimitQueue(GetMixinTester):
    QueueClass = RateLimitQueue

    def test_fifo(self):
        rlq = self.QueueClass(per=0)
        rlq.put(1)
        rlq.put(2)
        assert rlq.get() == 1
        assert rlq.get() == 2


class TestRateLimitLifoQueue(GetMixinTester):
    QueueClass = RateLimitLifoQueue

    def test_lifo(self):
        rlq = self.QueueClass(per=0)
        rlq.put(1)
        rlq.put(2)
        assert rlq.get() == 2
        assert rlq.get() == 1


class TestRateLimitPriorityQueue(GetMixinTester):
    QueueClass = RateLimitPriorityQueue

    def test_priority(self):
        rlq = self.QueueClass(per=0)

        rlq.put((4, "fourth"))
        rlq.put((2, "second"))
        rlq.put((1, "first"))
        rlq.put((3, "third"))

        assert rlq.get() == (1, "first")
        assert rlq.get() == (2, "second")
        assert rlq.get() == (3, "third")
        assert rlq.get() == (4, "fourth")
