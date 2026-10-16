"""Rendering for ``uuid.UUID`` -- imported only once a UUID is actually
captured."""
from __future__ import annotations


def render(value):
    return ('value', str(value))
