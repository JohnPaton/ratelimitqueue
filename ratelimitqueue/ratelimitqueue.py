import time
import random

import queue
import multiprocessing.dummy as mp

from .exceptions import RateLimitException
from . import utils


class RateLimitGetMixin:
    """Adds rate limiting to another class' `get()` method.

    Assumes that the class being extended has properties `calls` (int),
    `per` (float), `fuzz` (float), and `_call_log` (queue.Queue), else will
    raise AttributeError on call of get().
    """

    def get(self, block=True, timeout=None):
        """
        Get an item from the queue.

        If optional args `block` is True and `timeout` is None (the default),
        block if necessary until a free slot is available and the rate limit
        has not been reached. If `timeout` is a non-negative number, it blocks
        at most `timeout` seconds and raises the RateLimitException if
        the required rate limit waiting time is shorter than the given timeout,
        or the Empty exception if no item was available within that time.

        Otherwise (`block` is False), get an item on the queue if an item
        is immediately available and the rate limit has not been hit. Else
        raise the RateLimitException if waiting on the rate limit, or
        Empty exception if there is no item available in the queue. Timeout
        is ignored in this case.

        Parameters
        ----------
        block : bool, optional, default True
            Whether to block until an item can be gotten from the queue

        timeout : float, optional, default None
            The maximum amount of time to block for

        """
        start = time.time()
        if timeout is not None and timeout < 0:
            raise ValueError("`timeout` must be a non-negative number")

        # acquire lock
        self._acquire_or_raise(self._pending_get, block, timeout)

        # make sure child class has the required attributes
        self._check_attributes()

        # get snapshot of properties so no need to lock
        per = self.per
        fuzz = self.fuzz

        if self._call_log.qsize() >= self.calls:
            # get the earliest call in the queue
            first_call = self._call_log.get()

            time_since_call = time.time() - first_call

            if time_since_call < per:
                # sleep long enough that we don't
                # go over the calls per unit time
                if block:
                    time_remaining = utils.get_time_remaining(start, timeout)
                    sleep_time = per - time_since_call

                    # not enough time to complete sleep -> exception
                    if (
                        time_remaining is not None
                        and time_remaining < sleep_time
                    ):
                        self._call_log.task_done()
                        raise RateLimitException(
                            "Not enough time in timeout to wait for next item"
                        )
                    else:
                        time.sleep(sleep_time)

                # too fast but not blocking -> exception
                else:
                    self._call_log.task_done()
                    raise RateLimitException("Too many requests")

            self._call_log.task_done()

        # starting to load up the queue, don't hammer gets with all allowed
        # calls at once
        elif fuzz > 0:
            time_remaining = utils.get_time_remaining(start, timeout)
            fuzz_time = random.uniform(0, fuzz)

            if time_remaining is not None:
                # timeout is set, so leave a bit of leeway from time_remaining
                # to not time out due to fuzzing
                fuzz_time = min(fuzz_time, time_remaining - 0.01)

            time.sleep(fuzz_time)

        # get remaining timeout time for the call to super().get()
        time_remaining = utils.get_time_remaining(start, timeout)

        if time_remaining is not None and time_remaining <= 0:
            raise TimeoutError

        # log the call, release the lock, and return the next item
        self._call_log.put(time.time())
        self._pending_get.release()
        return super().get(block, timeout=time_remaining)

    def _check_attributes(self):
        """Check that calling object has properties calls, per, fuzz,
        _call_log, and get()"""
        if not hasattr(self, "calls"):
            raise AttributeError(
                "RateLimitGetMixin requires the `.calls` property"
            )

        if not hasattr(self, "per"):
            raise AttributeError(
                "RateLimitGetMixin requires the `.per` property"
            )

        if not hasattr(self, "fuzz"):
            raise AttributeError(
                "RateLimitGetMixin requires the `.fuzz` property"
            )

        if not hasattr(self, "_call_log"):
            raise AttributeError(
                "RateLimitGetMixin requires the `._call_log` Queue"
            )

        if not hasattr(super(), "get"):
            raise AttributeError(
                "RateLimitGetMixin must be mixed into a base class with"
                " the `.get()` method"
            )

    @staticmethod
    def _acquire_or_raise(lock, block=True, timeout=None):
        """Attempt to acquire `lock`, else raise RateLimitException"""
        if block and timeout is not None:
            locked = lock.acquire(block, timeout)
        else:
            locked = lock.acquire(block)

        if not locked:
            raise RateLimitException("Timed out waiting for next item")


class RateLimitQueue(RateLimitGetMixin, queue.Queue):
    def __init__(self, maxsize=0, calls=1, per=1.0, fuzz=0):
        """
        A thread safe queue with a given maximum size and rate limit.

        If `maxsize` is <= 0, the queue size is infinite (see
        `queue.Queue`).

        The rate limit is described as `calls` `per` time window, with
        `per` measured in seconds. The default rate limit is 1 call per
        second. If `per` is <= 0, the rate limit is infinite.

        To avoid immediately getting the maximum allowed items at startup, an
        extra randomized wait period can be configured with `fuzz`.
        This will cause the RateLimitQueue to wait between 0 and `fuzz`
        seconds before getting the object in the queue. Fuzzing only
        occurs if there is no rate limit waiting to be done.

        Parameters
        ----------
        maxsize : int, optional, default 0
            The number of slots in the queue, <=0 for infinite.

        calls : int, optional, default 1
            The number of call per time unit `per`. Must be at least 1.

        per : float, optional, default 1.0
            The time window for tracking calls, in seconds, <=0 for
            infinite rate limit.

        fuzz: float, options, default 0
            The maximum length (in seconds) of fuzzed extra sleep, <=0
            for no fuzzing

        Examples
        --------

        Basic usage:

            >>> rlq = RateLimitQueue()
            >>> rlq.put(1)
            >>> rlq.put(2)
            >>> rlq.get()
            1
            >>> rlq.get()
            2

        A rate limit of 3 calls per 5 seconds:

            >>> rlq = RateLimitQueue(calls=3, per=5)

        A queue with the default 1 call per second, with a maximum size
        of 3:

            >>> rlq = RateLimitQueue(3)

        A queue of infinite size and rate limit, equivalent to
        queue.Queue():

            >>> rlq = RateLimitQueue(per=0)

        A queue with wait time fuzzing up to 1 second so that the queue
        cannot be filled immediately directly after instantiation:

            >>> rlq = RateLimitQueue(fuzz=1)

        """
        if calls < 1:
            raise ValueError("`calls` must be an integer >= 1")

        super().__init__(maxsize)
        self.calls = int(calls)
        self.per = float(per)
        self.fuzz = float(fuzz)

        self._call_log = queue.Queue(maxsize=self.calls)
        self._pending_get = mp.Lock()


class RateLimitLifoQueue(RateLimitGetMixin, queue.LifoQueue):
    def __init__(self, maxsize=0, calls=1, per=1.0, fuzz=0):
        """
        A thread safe LIFO queue with a given maximum size and rate limit.

        If `maxsize` is <= 0, the queue size is infinite (see
        `queue.LifoQueue`).

        The rate limit is described as `calls` `per` time window, with
        `per` measured in seconds. The default rate limit is 1 call per
        second. If `per` is <= 0, the rate limit is infinite.

        To avoid immediately filling the whole queue at startup, an
        extra randomized wait period can be configured with `fuzz`.
        This will cause the RateLimitQueue to wait between 0 and `fuzz`
        seconds before putting the object in the queue. Fuzzing only
        occurs if there is no rate limit waiting to be done.

        Parameters
        ----------
        maxsize : int, optional, default 0
            The number of slots in the queue, <=0 for infinite.

        calls : int, optional, default 1
            The number of call per time unit `per`. Must be at least 1.

        per : float, optional, default 1.0
            The time window for tracking calls, in seconds, <=0 for
            infinite rate limit.

        fuzz: float, options, default 0
            The maximum length (in seconds) of fuzzed extra sleep, <=0
            for no fuzzing

        Examples
        --------
        Basic usage:

            >>> rlq = RateLimitLifoQueue()
            >>> rlq.put(1)
            >>> rlq.put(2)
            >>> rlq.get()
            2
            >>> rlq.get()
            1

        A rate limit of 3 calls per 5 seconds:

            >>> rlq = RateLimitLifoQueue(calls=3, per=5)

        A queue with the default 1 call per second, with a maximum size
        of 3:

            >>> rlq = RateLimitLifoQueue(3)

        A queue of infinite size and rate limit, equivalent to
        queue.Queue():

            >>> rlq = RateLimitLifoQueue(per=0)

        A queue with wait time fuzzing up to 1 second so that the queue
        cannot be filled immediately directly after instantiation:

            >>> rlq = RateLimitLifoQueue(fuzz=1)

        """
        if calls < 1:
            raise ValueError("`calls` must be an integer >= 1")

        super().__init__(maxsize)
        self.calls = int(calls)
        self.per = float(per)
        self.fuzz = float(fuzz)

        self._call_log = queue.Queue(maxsize=self.calls)
        self._pending_get = mp.Lock()


class RateLimitPriorityQueue(RateLimitGetMixin, queue.PriorityQueue):
    def __init__(self, maxsize=0, calls=1, per=1.0, fuzz=0):
        """
        A thread safe priority queue with a given maximum size and rate
        limit.

        Prioritized items should be tuples of form (priority, item), with
        priority lowest first. Priority determines the order of items
        returned by get().

        If `maxsize` is <= 0, the queue size is infinite (see
        `queue.LifoQueue`).

        The rate limit is described as `calls` `per` time window, with
        `per` measured in seconds. The default rate limit is 1 call per
        second. If `per` is <= 0, the rate limit is infinite.

        To avoid immediately filling the whole queue at startup, an
        extra randomized wait period can be configured with `fuzz`.
        This will cause the RateLimitQueue to wait between 0 and `fuzz`
        seconds before putting the object in the queue. Fuzzing only
        occurs if there is no rate limit waiting to be done.

        Parameters
        ----------
        maxsize : int, optional, default 0
            The number of slots in the queue, <=0 for infinite.

        calls : int, optional, default 1
            The number of call per time unit `per`. Must be at least 1.

        per : float, optional, default 1.0
            The time window for tracking calls, in seconds, <=0 for
            infinite rate limit.

        fuzz: float, options, default 0
            The maximum length (in seconds) of fuzzed extra sleep, <=0
            for no fuzzing

        Examples
        --------

        Basic usage:

            >>> rlq = RateLimitPriorityQueue()
            >>> rlq.put((2, 'second'))
            >>> rlq.put((1, 'first'))
            >>> rlq.get()
            (1, 'first')
            >>> rlq.get()
            (2, 'second')

        A rate limit of 3 calls per 5 seconds:

            >>> rlq = RateLimitPriorityQueue(calls=3, per=5)

        A queue with the default 1 call per second, with a maximum size
        of 3:

            >>> rlq = RateLimitPriorityQueue(3)

        A queue of infinite size and rate limit, equivalent to
        queue.Queue():

            >>> rlq = RateLimitPriorityQueue(per=0)

        A queue with wait time fuzzing up to 1 second so that the queue
        cannot be filled immediately directly after instantiation:

            >>> rlq = RateLimitPriorityQueue(fuzz=1)

        """
        if calls < 1:
            raise ValueError("`calls` must be an integer >= 1")

        super().__init__(maxsize)
        self.calls = int(calls)
        self.per = float(per)
        self.fuzz = float(fuzz)

        self._call_log = queue.Queue(maxsize=self.calls)
        self._pending_get = mp.Lock()
