# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Everything that can go wrong talking to Claude, as exceptions the rest of
the application can catch without knowing the SDK exists.

Catch :class:`ClaudeError` and show :attr:`ClaudeError.user_message`; catch
a subclass when the caller can do something specific about it (ask for the
key, wait and retry, offer to turn a setting off).
"""

from .. import check_types as _check_types


class ClaudeError(Exception):
    """Base class. *message* is for logs; :attr:`user_message` is for the user."""

    @_check_types.do
    def __init__(self, message: str, *, status_code: int | None = None, request_id: str | None = None,
                 details: str = '') -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.details = details

    @property
    @_check_types.do
    def user_message(self) -> str:
        """A sentence or two fit to show in a dialog or status bar."""
        return self.message


class NoApiKeyError(ClaudeError):
    """No API key is stored."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return 'No Anthropic API key is stored yet. Add your key in the Claude settings.'


class KeyStoreError(ClaudeError):
    """The system credential store could not be read or written."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return f'The system credential store failed: {self.message}'


class AuthenticationFailed(ClaudeError):
    """The API rejected the key (401) or the account may not do this (403)."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return ('Anthropic did not accept the API key or the account is not allowed to do this. '
                f'Check the key in the Claude settings. ({self.message})')


class RateLimited(ClaudeError):
    """429: too many requests or tokens. The SDK has already retried."""

    @_check_types.do
    def __init__(self, message: str, *, retry_after: float | None = None, status_code: int | None = None,
                 request_id: str | None = None) -> None:
        super().__init__(message, status_code=status_code, request_id=request_id)
        self.retry_after = retry_after

    @property
    @_check_types.do
    def user_message(self) -> str:
        if self.retry_after is not None:
            return f'Anthropic is rate limiting this key. Try again in about {self.retry_after:.0f} seconds.'

        return 'Anthropic is rate limiting this key. Try again in a minute.'


class ServiceUnavailable(ClaudeError):
    """5xx, overloaded, no connection, or timed out. The SDK has already retried."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return f'Could not reach Claude right now ({self.message}). Check the connection and try again.'


class BadRequest(ClaudeError):
    """400 / 404 / 413 / 422: the request itself was refused (a bug on our
    side, an unknown model, or too much text)."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return f'Claude refused the request: {self.message}'


class BetaNotAvailable(BadRequest):
    """The refusal-fallback beta is not enabled for this organisation."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return ('Your Anthropic organisation cannot use the refusal-fallback beta. '
                'Turn off "Retry refused requests on another model" in the Claude settings.')


class Refused(ClaudeError):
    """Claude declined to answer (a safety classifier fired)."""

    @_check_types.do
    def __init__(self, message: str, *, category: str | None = None, explanation: str | None = None,
                 request_id: str | None = None) -> None:
        super().__init__(message, request_id=request_id)
        self.category = category
        self.explanation = explanation

    @property
    @_check_types.do
    def user_message(self) -> str:
        text = 'Claude declined this request.'
        if self.explanation:
            text += f' {self.explanation}'

        return text


class Truncated(ClaudeError):
    """The answer hit ``max_tokens`` before it was finished."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return 'Claude ran out of room before finishing its answer. Try a smaller request.'


class Cancelled(ClaudeError):
    """The caller cancelled the request."""

    @_check_types.do
    def __init__(self, message: str = 'cancelled') -> None:
        super().__init__(message)

    @property
    @_check_types.do
    def user_message(self) -> str:
        return 'Cancelled.'


class InvalidStructuredReply(ClaudeError):
    """A structured-output request came back as something that is not JSON."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return 'Claude\'s answer could not be read as the structured data that was asked for.'


class ToolLoopLimit(ClaudeError):
    """Claude kept calling tools past the allowed number of rounds."""

    @property
    @_check_types.do
    def user_message(self) -> str:
        return 'Claude kept calling tools without finishing, so the request was stopped.'
