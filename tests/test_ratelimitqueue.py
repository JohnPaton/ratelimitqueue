"""Tests for ratelimitqueue/ratelimitqueue.py"""
import pytest
from unittest import mock
from .utils import almost

from ratelimitqueue.ratelimitqueue import RateLimitQueue, RateLimitException
from ratelimitqueue.ratelimitqueue import RateLimitLifoQueue
from ratelimitqueue.ratelimitqueue import RateLimitPriorityQueue

from queue import Full

import time
import random

# take randomness out of fuzzing
random.uniform = mock.MagicMock(return_value=0.5)

class PutMixinTester:
    # tests of __init__()
    def test_no_per(self):
        rlq = self.QueueClass()
        del rlq.per
        with pytest.raises(AttributeError):
            rlq.put(1)

    def test_no_fuzz(self):
        rlq = self.QueueClass()
        del rlq.fuzz
        with pytest.raises(AttributeError):
            rlq.put(1)

    def test_no__call_log(self):
        rlq = self.QueueClass()
        del rlq._call_log
        with pytest.raises(AttributeError):
            rlq.put(1)

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

    # tests of put()

    def test_timeout_not_less_than_0(self):
        rlq = self.QueueClass()
        with pytest.raises(ValueError):
            rlq.put(1, timeout=-1)

    def test_item_in_queue(self):
        rlq = self.QueueClass()
        rlq.put(1)
        assert rlq.get() == 1

    def test_first_put_fast(self):
        rlq = self.QueueClass()
        start = time.time()
        rlq.put(1)

        assert almost(0, time.time()-start)

    def test_default_rate_limit(self):
        rlq = self.QueueClass()
        start = time.time()

        rlq.put(1)
        rlq.put(1)

        assert almost(1, time.time()-start)

    def test_rate_limit_calls(self):
        rlq = self.QueueClass(calls=2)
        start = time.time()

        rlq.put(1)
        rlq.put(1)

        rlq.put(1)
        assert almost(1, time.time() - start)

        rlq.put(1)
        assert almost(1, time.time() - start)

    def test_rate_limit_per(self):
        rlq = self.QueueClass(per=0.5)
        start = time.time()

        rlq.put(1)
        rlq.put(1)
        rlq.put(1)

        assert almost(1, time.time() - start)

    def test_rate_limit_calls_per(self):
        rlq = self.QueueClass(calls=2, per=0.5)
        start = time.time()

        rlq.put(1)
        rlq.put(1)

        rlq.put(1)
        assert almost(0.5, time.time() - start)

        rlq.put(1)
        assert almost(0.5, time.time() - start)

    def test_not_block_raises_rate_limit(self):
        rlq = self.QueueClass(1, 1, 10)
        rlq.put(0)

        with pytest.raises(RateLimitException):
            rlq.put(1, block=False)

    def test_not_block_raises_full(self):
        rlq = self.QueueClass(1, 1, 0)
        rlq.put(0)

        with pytest.raises(Full):
            rlq.put(1, block=False)

    def test_timeout_on_rate_limit_raises_rate_limit(self):
        rlq = self.QueueClass(per=10)
        rlq.put(1)
        with pytest.raises(RateLimitException):
            rlq.put(2, timeout=1)

    def test_timeout_on_queue_size_raises_full(self):
        rlq = self.QueueClass(maxsize=1, per=0)
        rlq.put(1)
        with pytest.raises(Full):
            rlq.put(2, timeout=0.001)

    def test_timeout_on_queue_size_timing(self):
        rlq = self.QueueClass(maxsize=1, per=0)
        rlq.put(1)

        with pytest.raises(Full):
            start = time.time()
            rlq.put(1, timeout=0.5)
            assert almost(0.5, time.time()-start)

    def test_no_fuzz_when_at_rate_limit(self):
        rlq = self.QueueClass(per=0.5)
        rlq.put(1)

        rlq.fuzz = 1000

        start = time.time()
        rlq.put(1)
        assert almost(0.5, time.time()-start)

    def test_fuzz(self):
        rlq = self.QueueClass(per=0.5, fuzz=1)
        start = time.time()
        rlq.put(1)
        end = time.time()
        assert not almost(0, end-start)
        assert end-start < 1

    def test_fuzz_less_than_timeout(self):
        rlq = self.QueueClass(fuzz=10000)
        start = time.time()
        rlq.put(1, timeout=0.5)
        end = time.time()
        elapsed = end - start
        assert almost(0.5, elapsed)


class TestRateLimitQueue(PutMixinTester):
    QueueClass = RateLimitQueue

    def test_fifo(self):
        rlq = self.QueueClass(per=0)
        rlq.put(1)
        rlq.put(2)
        assert rlq.get() == 1
        assert rlq.get() == 2

class TestRateLimitLifoQueue(PutMixinTester):
    QueueClass = RateLimitLifoQueue

    def test_lifo(self):
        rlq = self.QueueClass(per=0)
        rlq.put(1)
        rlq.put(2)
        assert rlq.get() == 2
        assert rlq.get() == 1


class TestRateLimitPriorityQueue(PutMixinTester):
    QueueClass = RateLimitPriorityQueue

    def test_priority(self):
        rlq = self.QueueClass(per=0)

        rlq.put((4, 'fourth'))
        rlq.put((2, 'second'))
        rlq.put((1, 'first'))
        rlq.put((3, 'third'))

        assert rlq.get() == (1, 'first')
        assert rlq.get() == (2, 'second')
        assert rlq.get() == (3, 'third')
        assert rlq.get() == (4, 'fourth')
