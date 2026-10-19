# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The user's own Anthropic API key, kept in the system credential store.

The key is never part of the application, never in a project file, never in
the Config database, and never read from an environment variable: it lives
only in the operating system's credential store (Windows Credential
Manager, macOS Keychain, ...) through ``keyring``.
"""

from typing import Any

from . import errors as _errors
from .... import check_types as _check_types

SERVICE = 'HarnessDesigner'
USERNAME = 'anthropic_api_key'

# Anthropic API keys start with this; the settings dialog uses it to catch
# an obvious paste mistake. Nothing else rejects a key on its shape.
KEY_PREFIX = 'sk-ant-'


class MemoryKeyring:
    """A backend holding one key in memory, never stored anywhere. Lets the
    settings dialog test a key the user has typed but not yet saved."""

    @_check_types.do
    def __init__(self, key: str = '') -> None:
        self._key = key

    @_check_types.do
    def get_password(self, service: str, username: str) -> str | None:
        return self._key or None

    @_check_types.do
    def set_password(self, service: str, username: str, password: str) -> None:
        self._key = password

    @_check_types.do
    def delete_password(self, service: str, username: str) -> None:
        self._key = ''


class ApiKeyStore:
    """Read, write and clear the stored key.

    :param backend: Anything with keyring's ``get_password`` /
        ``set_password`` / ``delete_password`` functions. ``None`` means the
        real ``keyring`` module; tests pass an in-memory fake so they never
        touch the real credential store.
    """

    @_check_types.do
    def __init__(self, backend: Any = None, service: str = SERVICE, username: str = USERNAME) -> None:
        self._backend = backend
        self._service = service
        self._username = username

    @_check_types.do
    def has_key(self) -> bool:
        return self.get_key() is not None

    @_check_types.do
    def get_key(self) -> str | None:
        """The stored key, or ``None`` if there is none."""
        backend = self._keyring()
        try:
            key = backend.get_password(self._service, self._username)
        except self._keyring_errors().KeyringError as error:
            raise _errors.KeyStoreError(str(error)) from error

        if key is None or not key.strip():
            return None

        return key.strip()

    @_check_types.do
    def set_key(self, key: str) -> None:
        key = key.strip()
        if not key:
            raise ValueError('an empty key cannot be stored; use clear_key() to remove it')

        backend = self._keyring()
        try:
            backend.set_password(self._service, self._username, key)
        except self._keyring_errors().KeyringError as error:
            raise _errors.KeyStoreError(str(error)) from error

    @_check_types.do
    def clear_key(self) -> None:
        """Remove the stored key; fine if there is none."""
        backend = self._keyring()
        errors = self._keyring_errors()
        try:
            backend.delete_password(self._service, self._username)
        except errors.PasswordDeleteError:
            pass
        except errors.KeyringError as error:
            raise _errors.KeyStoreError(str(error)) from error

    @staticmethod
    @_check_types.do
    def looks_like_a_key(key: str) -> bool:
        """Whether *key* has the shape of an Anthropic key (advisory only)."""
        return key.strip().startswith(KEY_PREFIX)

    @_check_types.do
    def _keyring(self) -> Any:
        if self._backend is not None:
            return self._backend

        import keyring

        return keyring

    @_check_types.do
    def _keyring_errors(self) -> Any:
        import keyring.errors

        return keyring.errors
