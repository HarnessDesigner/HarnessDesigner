# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import re

_DIGIT_RUN = re.compile(r'(\d+)')


def natural_sort_key(name: str) -> tuple:
    """Split *name* into alternating text/number chunks (numeric chunks
    compared as ints) so ``"2"`` sorts before ``"10"`` -- a plain string
    sort relies on names being zero-padded to read in order, which real
    project data isn't guaranteed to be.

    Each chunk tagged ``(0, int)`` for a digit run or ``(1, str)`` for
    text -- comparing two chunks always compares the leading kind tag
    (int vs int) first, so same-position chunks of different kinds
    decide right there and never fall through to comparing an int
    against a str (a TypeError in Python 3).
    """
    return tuple(
        (0, int(chunk)) if chunk.isdigit() else (1, chunk.lower())
        for chunk in _DIGIT_RUN.split(name) if chunk)
