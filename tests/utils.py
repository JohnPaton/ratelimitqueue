import math


def almost(a, b, threshold=0.01):
    """
    Test whether `a` and `b` within `threshold` of each other.

    Useful for timing related asserts where the timing is not 100%
    certain but should be close to a given number.

    Parameters
    ----------
    a: float
    b: float
    threshold: float (default 0.01)

    Returns
    -------
    bool
    """
    return math.fabs(a - b) < threshold
