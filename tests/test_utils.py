"""Tests for ratelimitqueue/utils.py"""
import time

from ratelimitqueue import utils

from .utils import almost


class TestGetTimeRemaining:
    def test_timeout_none(self):
        assert utils.get_time_remaining(0, None) is None

    def test_timeout_positive(self):
        start = time.time()
        remaining = utils.get_time_remaining(start, 5)
        assert almost(remaining, 5)

    def test_timeout_zero(self):
        start = time.time()
        remaining = utils.get_time_remaining(start, 0)
        assert almost(remaining, 0)

    def test_timeout_negative(self):
        start = time.time()
        remaining = utils.get_time_remaining(start, -5)
        assert almost(remaining, -5)

    def test_timeout_passed(self):
        start = time.time() + 10
        remaining = utils.get_time_remaining(start, 5)
        assert almost(remaining, -5)
