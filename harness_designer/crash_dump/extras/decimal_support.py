"""Rendering for ``decimal.Decimal`` -- imported only once a Decimal is
actually captured."""
from __future__ import annotations


def render(value):
    return ('value', str(value))
