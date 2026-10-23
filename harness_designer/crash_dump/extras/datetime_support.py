"""Rendering for ``datetime.datetime``/``datetime.date`` -- imported only
once one is actually captured."""
from __future__ import annotations

from ... import check_types as _check_types


@_check_types.do
def render(value):
    return ('value', value.isoformat())
