"""Tests for tests/utils.py"""
from . import utils


class TestAlmost:
    def test_above_threshold(self):
        assert utils.almost(0, 1, 0) is False

    def test_below_threshold(self):
        assert utils.almost(0, 0, 1) is True

    def test_b_less_than_a(self):
        assert utils.almost(1, 0) is False
        assert utils.almost(1, 0.99, 0.1) is True

    def test_negative_threshold(self):
        assert utils.almost(0, 0, -1) is False
        assert utils.almost(1, 0, -1) is False
        assert utils.almost(0, 1, -1) is False
