# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The one object the rest of the application uses to talk to Claude.

It owns the SDK client (built from the user's stored key), turns SDK errors
into this package's own, streams every request so that nothing times out and
anything can be cancelled, and keeps a running total of what has been used.
"""

from typing import Any

import threading
import traceback

from . import cancel as _cancel
from . import context as _context
from . import conversation as _conversation
from . import errors as _errors
from . import keys as _keys
from . import messages as _messages
from . import settings as _settings
from .... import check_types as _check_types

CHECK_PROMPT = 'Reply with the single word OK.'


@_check_types.do
def warm_up() -> threading.Thread:
    """Import the Anthropic SDK on a background thread.

    The first import takes about three seconds, which would otherwise be the
    delay before the very first answer starts. Call this when something that
    uses Claude is opened (an assistant panel, the settings dialog); it is
    harmless to call again. Returns the thread (already started).
    """
    @_check_types.do
    def load() -> None:
        import anthropic  # NOQA -- imported for its side effect: the module is cached afterwards

    thread = threading.Thread(target=load, name='ClaudeWarmUp', daemon=True)
    thread.start()
    return thread


class ClaudeClient:
    """
    :param key_store: Where the API key is. Default: the system credential store.
    :param settings: Fixed settings for this client. Default: follow the
        application-wide settings (:func:`harness_designer.claude.settings.current`)
        as they are at each call, so changing them in the settings dialog
        applies to the next request.
    :param base_url: Send requests somewhere else than Anthropic (used by the
        tests, which talk to a fake server).
    """

    @_check_types.do
    def __init__(self, key_store: _keys.ApiKeyStore | None = None, settings: _settings.ClaudeSettings | None = None,
                 *, base_url: str | None = None) -> None:
        self._key_store = key_store or _keys.ApiKeyStore()
        self._settings = settings
        self._base_url = base_url

        self._sdk_lock = threading.Lock()
        self._sdk_client: Any = None
        self._sdk_signature: tuple | None = None

        self._usage_lock = threading.Lock()
        self._usage = _messages.Usage()

    # -- state --------------------------------------------------------------

    @property
    @_check_types.do
    def settings(self) -> _settings.ClaudeSettings:
        """The settings that apply to the next request."""
        if self._settings is not None:
            return self._settings

        return _settings.current()

    @property
    @_check_types.do
    def key_store(self) -> _keys.ApiKeyStore:
        return self._key_store

    @property
    @_check_types.do
    def usage(self) -> _messages.Usage:
        """Everything this client has used since it was created."""
        with self._usage_lock:
            return self._usage

    @_check_types.do
    def record_usage(self, usage: _messages.Usage) -> None:
        """Add to the running total (called by conversations)."""
        with self._usage_lock:
            self._usage = self._usage + usage

    @_check_types.do
    def derive(self, *, key: str | None = None, settings: _settings.ClaudeSettings | None = None) -> 'ClaudeClient':
        """A client like this one but using *key* (not stored anywhere) and/or
        fixed *settings*. Used to test what the user has typed before saving."""
        key_store = self._key_store
        if key is not None:
            key_store = _keys.ApiKeyStore(backend=_keys.MemoryKeyring(key))

        return ClaudeClient(key_store, settings or self._settings, base_url=self._base_url)

    # -- making requests ----------------------------------------------------

    @_check_types.do
    def conversation(self, *, system: str | None = None, tools: list[_messages.Tool] | None = None,
                     context: list[_context.ContextProvider] | None = None, topic: str = '',
                     output_schema: dict[str, Any] | None = None, model: str | None = None,
                     effort: str | None = None, max_tokens: int | None = None,
                     max_tool_rounds: int = _conversation.DEFAULT_MAX_TOOL_ROUNDS) -> _conversation.Conversation:
        """Start a conversation. Its model, tools and system prompt are fixed
        from here on (see :class:`Conversation`); *model*, *effort* and
        *max_tokens* override the application settings for this conversation
        only."""
        settings = self.settings.changed()
        overrides: dict[str, Any] = {}
        if model is not None:
            overrides['model'] = model
        if effort is not None:
            overrides['effort'] = effort
        if max_tokens is not None:
            overrides['max_tokens'] = max_tokens

        if overrides:
            settings = settings.changed(**overrides)

        return _conversation.Conversation(
            self, settings, system=system, tools=tools, context=context, topic=topic,
            output_schema=output_schema, max_tool_rounds=max_tool_rounds)

    @_check_types.do
    def ask(self, prompt: str, *, system: str | None = None, tools: list[_messages.Tool] | None = None,
            context: list[_context.ContextProvider] | None = None, topic: str = '',
            output_schema: dict[str, Any] | None = None, model: str | None = None, effort: str | None = None,
            max_tokens: int | None = None, on_text: _conversation.TextCallback | None = None,
            on_tool: _conversation.ToolCallback | None = None,
            cancel: _cancel.CancelToken | None = None) -> _messages.Response:
        """One question, one answer (tools run if given). For anything that
        goes on longer than that, use :meth:`conversation`."""
        chat = self.conversation(
            system=system, tools=tools, context=context, topic=topic, output_schema=output_schema, model=model,
            effort=effort, max_tokens=max_tokens)
        return chat.send(prompt, on_text=on_text, on_tool=on_tool, cancel=cancel)

    @_check_types.do
    def check_connection(self, cancel: _cancel.CancelToken | None = None) -> _messages.Response:
        """A tiny real request, to confirm the key and the settings work.
        Costs a fraction of a cent."""
        return self.ask(CHECK_PROMPT, effort='low', max_tokens=1024, cancel=cancel)

    # -- the network --------------------------------------------------------

    @_check_types.do
    def stream_message(self, params: dict[str, Any], beta: bool, on_text: _conversation.TextCallback | None,
                       cancel: _cancel.CancelToken) -> tuple[Any, str | None]:
        """Make one streaming request; returns the finished SDK message and
        the API's id for the request (a streamed message does not carry it).

        :param beta: Use the beta endpoint (needed for the refusal fallback).
        :raises ClaudeError: Any failure, already translated.
        """
        sdk = self._sdk()
        if beta:
            endpoint = sdk.beta.messages
        else:
            endpoint = sdk.messages

        try:
            with endpoint.stream(**params) as stream:
                # Closing the stream from another thread is what unblocks a
                # read that is waiting on a slow answer.
                cancel.add_callback(stream.close)
                try:
                    for event in stream:
                        if cancel.is_cancelled:
                            raise _errors.Cancelled()

                        if event.type == 'text' and on_text is not None:
                            on_text(event.text)

                    message = stream.get_final_message()
                    request_id = stream.response.headers.get('request-id')
                finally:
                    cancel.remove_callback(stream.close)
        except _errors.ClaudeError:
            raise
        except Exception as error:  # NOQA -- translated into this package's own errors
            if cancel.is_cancelled:
                raise _errors.Cancelled() from error

            raise self._translate(error) from error

        return message, request_id

    @_check_types.do
    def _sdk(self) -> Any:
        key = self._key_store.get_key()
        if key is None:
            raise _errors.NoApiKeyError('no API key is stored')

        settings = self.settings
        signature = (key, settings.max_retries, settings.timeout_seconds, self._base_url)

        with self._sdk_lock:
            if self._sdk_signature != signature:
                import anthropic

                options: dict[str, Any] = {
                    'api_key': key, 'max_retries': settings.max_retries, 'timeout': settings.timeout_seconds}
                if self._base_url is not None:
                    options['base_url'] = self._base_url

                previous = self._sdk_client
                self._sdk_client = anthropic.Anthropic(**options)
                self._sdk_signature = signature
                if previous is not None:
                    previous.close()

            return self._sdk_client

    @_check_types.do
    def _translate(self, error: Exception) -> _errors.ClaudeError:
        """An SDK exception as one of this package's, most specific first."""
        import anthropic

        details = ''.join(traceback.format_exception(error))

        if isinstance(error, anthropic.APIStatusError):
            status = error.status_code
            request_id = error.request_id
            message = error.message

            if status in (401, 403):
                return _errors.AuthenticationFailed(message, status_code=status, request_id=request_id, details=details)

            if status == 429:
                return _errors.RateLimited(
                    message, retry_after=self._retry_after(error), status_code=status, request_id=request_id)

            if status == 400 and 'anthropic-beta' in message:
                return _errors.BetaNotAvailable(message, status_code=status, request_id=request_id, details=details)

            if status in (400, 404, 413, 422):
                return _errors.BadRequest(message, status_code=status, request_id=request_id, details=details)

            if status >= 500:
                return _errors.ServiceUnavailable(message, status_code=status, request_id=request_id, details=details)

            return _errors.ClaudeError(message, status_code=status, request_id=request_id, details=details)

        if isinstance(error, anthropic.APITimeoutError):
            return _errors.ServiceUnavailable('the request timed out', details=details)

        if isinstance(error, anthropic.APIConnectionError):
            return _errors.ServiceUnavailable(str(error) or 'connection failed', details=details)

        return _errors.ClaudeError(f'{type(error).__name__}: {error}', details=details)

    @_check_types.do
    def _retry_after(self, error: Any) -> float | None:
        value = error.response.headers.get('retry-after')
        if value is None:
            return None

        try:
            return float(value)
        except ValueError:
            return None
