# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared test fixtures for the Claude package."""

import keyring.errors


class FakeKeyring:
    """An in-memory stand-in for the ``keyring`` module's three functions.

    Tests must never use the real credential store (on this machine that is
    Windows Credential Manager, which holds the user's real key).
    """

    def __init__(self):
        self.passwords: dict[tuple[str, str], str] = {}
        self.fail_with: Exception | None = None

    def get_password(self, service, username):
        if self.fail_with is not None:
            raise self.fail_with

        return self.passwords.get((service, username))

    def set_password(self, service, username, password):
        if self.fail_with is not None:
            raise self.fail_with

        self.passwords[(service, username)] = password

    def delete_password(self, service, username):
        if self.fail_with is not None:
            raise self.fail_with

        if (service, username) not in self.passwords:
            raise keyring.errors.PasswordDeleteError('not found')

        del self.passwords[(service, username)]
