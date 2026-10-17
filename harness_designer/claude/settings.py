# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The user's Claude settings, shared by everything that calls Claude.

One model choice and one effort level for the whole application, changed in
one place (the settings dialog) and picked up by every caller. A caller that
needs something different for one request passes it to that request.

Where the values are *persisted* is the application's business, not this
package's: call :func:`set_backend` once at startup with an object that can
load and save a plain dict (the Config database is the obvious one). With no
backend the settings live in memory and reset on restart.
"""

from typing import Any

from dataclasses import asdict, dataclass, fields, replace

import threading

from . import models as _models
from .. import check_types as _check_types


@dataclass
class ClaudeSettings:
    """
    :ivar model: Model id (see :mod:`~harness_designer.claude.models`).
    :ivar effort: ``output_config.effort`` -- how hard Claude thinks.
    :ivar max_tokens: Upper limit on one answer (a cap, not a charge).
    :ivar refusal_fallback: When a safety classifier declines, let Anthropic
        retry the request on another model server-side.
    :ivar max_retries: How often the SDK retries rate limits / server errors.
    :ivar timeout_seconds: Per-request network timeout.
    """

    model: str = _models.DEFAULT_MODEL
    effort: str = _models.DEFAULT_EFFORT
    max_tokens: int = 64000
    refusal_fallback: bool = True
    max_retries: int = 2
    timeout_seconds: float = 600.0

    @_check_types.do
    def validate(self) -> None:
        """:raises ValueError: A value cannot be sent to the API."""
        if not self.model.strip():
            raise ValueError('model must not be empty')

        if self.effort not in _models.EFFORTS:
            raise ValueError(f'effort must be one of {", ".join(_models.EFFORTS)}')

        if self.max_tokens < 1:
            raise ValueError('max_tokens must be at least 1')

        if self.max_retries < 0:
            raise ValueError('max_retries cannot be negative')

        if self.timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be positive')

    @_check_types.do
    def changed(self, **changes: dict[str, Any]) -> 'ClaudeSettings':
        """A validated copy with *changes* applied."""
        updated = replace(self, **changes)
        updated.validate()
        return updated

    @property
    @_check_types.do
    def uses_fallback(self) -> bool:
        """Whether requests with these settings carry the refusal fallback:
        it is switched on and the model has one."""
        info = _models.model_info(self.model)
        return self.refusal_fallback and info is not None and info.supports_fallback


class SettingsBackend:
    """Where settings are persisted. The application supplies one."""

    @_check_types.do
    def load(self) -> dict[str, object]:
        """The saved values (any subset of the settings' field names)."""
        raise NotImplementedError

    @_check_types.do
    def save(self, values: dict[str, object]) -> None:
        """Store all the settings' values."""
        raise NotImplementedError


_lock = threading.Lock()
_current = ClaudeSettings()
_backend: SettingsBackend | None = None


@_check_types.do
def current() -> ClaudeSettings:
    """The settings in force right now (a copy: change them with :func:`update`)."""
    with _lock:
        return replace(_current)


@_check_types.do
def update(**changes: dict[str, Any]) -> ClaudeSettings:
    """Change settings, validate them, persist them, and return the result.

    :raises ValueError: A value is not acceptable; nothing is changed.
    """
    global _current

    with _lock:
        updated = _current.changed(**changes)
        backend = _backend
        if backend is not None:
            backend.save(asdict(updated))

        _current = updated
        return replace(updated)


@_check_types.do
def set_backend(backend: SettingsBackend | None) -> ClaudeSettings:
    """Use *backend* for persistence, loading what it has saved.

    Values the backend returns that are not settings, or are not valid, are
    ignored (a database written by a newer version must not stop startup);
    the rest replace the defaults.
    """
    global _current, _backend

    with _lock:
        _backend = backend
        settings = ClaudeSettings()

        if backend is not None:
            known = {field.name for field in fields(ClaudeSettings)}
            saved = {name: value for name, value in backend.load().items() if name in known}
            for name, value in saved.items():
                try:
                    settings = settings.changed(**{name: value})
                except (TypeError, ValueError):
                    continue

        _current = settings
        return replace(settings)
