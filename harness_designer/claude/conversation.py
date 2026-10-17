# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""An exchange with Claude: one question, or a long back-and-forth with tools.

The one rule that shapes this class (CLAUDE_API_DESIGN.md): **a conversation
is append-only.** Its model, tools and system prompt are fixed when it is
created, and its history only ever grows. Claude's thinking is bound to the
conversation that produced it, so changing anything earlier and replaying
the thinking is an API error, and it throws away the prompt cache besides.
Knowledge that turns up later goes in with :meth:`Conversation.note`.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import json
import threading

from . import cancel as _cancel
from . import context as _context
from . import errors as _errors
from . import messages as _messages
from . import settings as _settings
from . import wire as _wire
from .. import check_types as _check_types

if TYPE_CHECKING:
    from . import client as _client

# Longest chain of "Claude asked for tools, we answered" in one send().
DEFAULT_MAX_TOOL_ROUNDS = 25

FALLBACK_BETA = 'server-side-fallback-2026-07-01'

TextCallback = Callable[[str], None]
ToolCallback = Callable[[str, dict[str, Any], str, bool], None]


class Conversation:
    """Create one with :meth:`~harness_designer.claude.ClaudeClient.conversation`.

    One :meth:`send` at a time: a second thread calling it waits.
    """

    @_check_types.do
    def __init__(self, client: "_client.ClaudeClient", settings: _settings.ClaudeSettings, *,
                 system: str | None = None, tools: list[_messages.Tool] | None = None,
                 context: list[_context.ContextProvider] | None = None, topic: str = '',
                 output_schema: dict[str, Any] | None = None,
                 max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS) -> None:
        settings.validate()
        tools = list(tools or [])

        names = [tool.name for tool in tools]
        if len(set(names)) != len(names):
            raise ValueError('two tools have the same name')

        self._client = client
        self._settings = settings
        self._system = _context.compose_system(system, list(context or []), topic)
        self._tools = {tool.name: tool for tool in tools}
        # Sorted: a different order is a different prompt prefix.
        self._tool_params = [self._tools[name].to_param() for name in sorted(self._tools)]
        self._schema = output_schema
        self._max_rounds = max_tool_rounds

        self._messages: list[Any] = []
        self._notes: list[str] = []
        self._turn_lock = threading.Lock()
        self._usage = _messages.Usage()

    # -- what the conversation is -------------------------------------------

    @property
    @_check_types.do
    def settings(self) -> _settings.ClaudeSettings:
        """The settings this conversation was created with (a copy)."""
        return self._settings.changed()

    @property
    @_check_types.do
    def system_prompt(self) -> str | None:
        """The frozen system prompt, background included."""
        return self._system

    @property
    @_check_types.do
    def usage(self) -> _messages.Usage:
        """Tokens used by every send() so far, failed ones included."""
        return self._usage

    @property
    @_check_types.do
    def turns(self) -> int:
        """How many messages are in the history."""
        return len(self._messages)

    # -- talking ------------------------------------------------------------

    @_check_types.do
    def note(self, text: str) -> None:
        """Tell Claude something it should take into account from the next
        :meth:`send` on -- a decision the user just made, a fact that turned
        up. It is added as an operator note after the user's next message;
        the system prompt is never touched."""
        text = text.strip()
        if text:
            self._notes.append(text)

    @_check_types.do
    def send(self, content: str | list[dict[str, Any]], *, on_text: TextCallback | None = None,
             on_tool: ToolCallback | None = None, cancel: _cancel.CancelToken | None = None) -> _messages.Response:
        """Say *content* and run until Claude has finished answering.

        :param content: Text, or a list of content blocks.
        :param on_text: Called with each piece of Claude's answer as it
            arrives (on the calling thread).
        :param on_tool: Called after each tool ran: (name, arguments,
            result text, is_error).
        :param cancel: Stop the call from another thread.
        :raises ClaudeError: Anything that went wrong; the conversation is
            left exactly as it was before this call (the failed exchange is
            not kept), so it can be sent again.
        """
        token = cancel or _cancel.CancelToken()

        with self._turn_lock:
            mark = len(self._messages)
            notes = self._notes
            self._notes = []

            self._messages.append({'role': 'user', 'content': content})
            for note in notes:
                self._messages.append({'role': 'system', 'content': note})

            try:
                return self._run(token, on_text, on_tool)
            except BaseException:
                del self._messages[mark:]
                self._notes = notes + self._notes
                raise

    # -- the loop -----------------------------------------------------------

    @_check_types.do
    def _run(self, token: _cancel.CancelToken, on_text: TextCallback | None,
             on_tool: ToolCallback | None) -> _messages.Response:
        usage = _messages.Usage()
        tool_calls = 0
        rounds = 0
        beta = self._settings.uses_fallback

        for _ in range(self._max_rounds):
            token.raise_if_cancelled()
            rounds += 1

            message, request_id = self._client.stream_message(self._params(), beta, on_text, token)

            round_usage = _wire.message_usage(message, beta)
            usage = usage + round_usage
            self._usage = self._usage + round_usage
            self._client.record_usage(round_usage)

            reason = message.stop_reason
            if reason == 'refusal':
                raise self._refusal(message, request_id)

            content = _wire.echo_content(message.content)
            self._messages.append({'role': 'assistant', 'content': content})

            if reason == 'max_tokens':
                raise _errors.Truncated('the answer hit max_tokens', request_id=request_id)

            uses = _wire.tool_uses(content)
            if reason == 'tool_use' and uses:
                results = self._run_tools(uses, token, on_tool)
                self._messages.append({'role': 'user', 'content': results})
                tool_calls += len(uses)
                continue

            if reason == 'pause_turn':
                continue

            return self._response(message, request_id, usage, tool_calls, rounds, beta)

        raise _errors.ToolLoopLimit(f'more than {self._max_rounds} rounds of tool calls')

    @_check_types.do
    def _run_tools(self, uses: list, token: _cancel.CancelToken, on_tool: ToolCallback | None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for block in uses:
            token.raise_if_cancelled()
            arguments = dict(block.input)
            tool = self._tools.get(block.name)
            is_error = False

            if tool is None:
                text = f'There is no tool called {block.name!r}.'
                is_error = True
            else:
                try:
                    text = _messages.result_text(tool.handler(arguments))
                except _errors.Cancelled:
                    raise
                except Exception as error:  # NOQA -- a tool is caller code: its failure is the model's to hear about
                    text = f'{type(error).__name__}: {error}'
                    is_error = True

            result: dict[str, Any] = {'type': 'tool_result', 'tool_use_id': block.id, 'content': text}
            if is_error:
                result['is_error'] = True

            results.append(result)
            if on_tool is not None:
                on_tool(block.name, arguments, text, is_error)

        return results

    @_check_types.do
    def _params(self) -> dict[str, Any]:
        """The request, built fresh each round from fixed pieces plus the
        history."""
        settings = self._settings
        output_config: dict[str, Any] = {'effort': settings.effort}
        if self._schema is not None:
            output_config['format'] = {'type': 'json_schema', 'schema': self._schema}

        params: dict[str, Any] = {
            'model': settings.model,
            'max_tokens': settings.max_tokens,
            'messages': self._messages,
            'output_config': output_config,
            # Caches the longest stable prefix automatically; costs nothing
            # when the prefix is too short to be cacheable.
            'cache_control': {'type': 'ephemeral'}}

        if self._system is not None:
            params['system'] = self._system

        if self._tool_params:
            params['tools'] = self._tool_params

        if settings.uses_fallback:
            params['betas'] = [FALLBACK_BETA]
            params['fallbacks'] = 'default'

        return params

    @_check_types.do
    def _refusal(self, message: Any, request_id: str | None) -> _errors.Refused:
        category = None
        explanation = None
        if message.stop_details is not None:
            category = message.stop_details.category
            explanation = message.stop_details.explanation

        return _errors.Refused('Claude declined the request', category=category, explanation=explanation,
                               request_id=request_id)

    @_check_types.do
    def _response(self, message: Any, request_id: str | None, usage: _messages.Usage, tool_calls: int,
                  rounds: int, beta: bool) -> _messages.Response:
        text = _wire.message_text(message)
        data = None

        if self._schema is not None:
            try:
                data = json.loads(text)
            except ValueError as error:
                raise _errors.InvalidStructuredReply(
                    f'the reply is not valid JSON: {error}', request_id=request_id,
                    details=text[:2000]) from error

        return _messages.Response(
            text=text,
            data=data,
            stop_reason=message.stop_reason,
            model=message.model,
            requested_model=self._settings.model,
            usage=usage,
            request_id=request_id,
            tool_calls=tool_calls,
            rounds=rounds,
            served_by_fallback=_wire.served_by_fallback(message, beta))
