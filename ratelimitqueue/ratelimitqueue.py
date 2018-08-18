import time
import random

import queue

from .exceptions import RateLimitException
from .utils import get_time_remaining


class RateLimitPutMixin:
    """Adds rate limiting to another class' `put()` method.

    Assumes that the class being extended has properties `per` (float),
    `fuzz` (float), and `_call_log` (queue.Queue), else will raise
    AttributeError on call of put().
    """

    def put(self, item, block=True, timeout=None):
        """
        Put an item into the queue.

        If optional args `block` is True and `timeout` is None (the default),
        block if necessary until a free slot is available and the rate limit
        has not been reached. If `timeout` is a non-negative number, it blocks
        at most `timeout` seconds and raises the RateLimitException if
        the required rate limit waiting time is shorter than the given timeout,
        or the Full exception if no free slot was available within that time.

        Otherwise (`block` is False), put an item on the queue if a free slot
        is immediately available and the rate limit has not been hit. Else
        raise the RateLimitException if waiting on the rate limit, or
        Full exception if there is no slot available in the queue. Timeout
        is ignored in this case.

        Parameters
        ----------
        item : obj
            The object to put in the queue

        block : bool, optional, default True
            Whether to block until the item can be put into the queue

        timeout : float, optional, default None
            The maximum amount of time to block for

        """
        start = time.time()

        if timeout is not None and timeout < 0:
            raise ValueError("`timeout` must be a non-negative number")

        if not hasattr(self, "per"):
            raise AttributeError("RateLimitPut requires the `.per` property")

        if not hasattr(self, "fuzz"):
            raise AttributeError("RateLimitPut requires the `.fuzz` property")

        if not hasattr(self, "_call_log"):
            raise AttributeError(
                "RateLimitPut requires the `._call_log` Queue"
            )

        if not hasattr(super(), "put"):
            raise AttributeError(
                "RateLimitPut must be mixed into a base class with"
                " the `.put()` method"
            )

        # get snapshot of properties so no need to lock
        per = self.per
        fuzz = self.fuzz

        if self._call_log.full():
            # get the earliest call in the queue
            first_call = self._call_log.get()
            self._call_log.task_done()

            time_since_call = time.time() - first_call

            if time_since_call < per:
                # sleep long enough that we don't
                # go over the calls per unit time
                if block:
                    time_remaining = get_time_remaining(start, timeout)
                    sleep_time = per - time_since_call

                    # not enough time to sleep
                    if (
                        time_remaining is not None
                        and time_remaining < sleep_time
                    ):
                        raise RateLimitException(
                            "Not enough time in timeout to wait for next slot"
                        )

                    time.sleep(sleep_time)

                # too fast but not blocking -> exception
                else:
                    raise RateLimitException("Too many requests")

        elif fuzz > 0:
            time_remaining = get_time_remaining(start, timeout)
            fuzz_time = random.uniform(0, fuzz)

            if time_remaining is not None:
                # leave a bit of leeway from time_remaining to not
                # time out due to fuzzing
                fuzz_time = min(fuzz_time, time_remaining - 0.01)

            time.sleep(fuzz_time)

        # get remaining timeout time for the call to put()
        time_remaining = get_time_remaining(start, timeout)

        if time_remaining is not None and time_remaining <= 0:
            raise TimeoutError

        super().put(item, block, timeout=time_remaining)

        # log the call
        self._call_log.put(time.time())


class RateLimitQueue(RateLimitPutMixin, queue.Queue):
    def __init__(self, maxsize=0, calls=1, per=1.0, fuzz=0):
        """
        A thread safe queue with a given maximum size and rate limit.

        If `maxsize` is <= 0, the queue size is infinite (see
        `queue.Queue`).

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


class RateLimitLifoQueue(RateLimitPutMixin, queue.LifoQueue):
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


class RateLimitPriorityQueue(RateLimitPutMixin, queue.PriorityQueue):
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
