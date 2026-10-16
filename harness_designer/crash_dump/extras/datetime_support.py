"""Rendering for ``datetime.datetime``/``datetime.date`` -- imported only
once one is actually captured."""
from __future__ import annotations


def render(value):
    return ('value', value.isoformat())
