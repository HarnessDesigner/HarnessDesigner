# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Reading what the SDK hands back.

Everything that touches the shape of an SDK message lives here, so the rest
of the package (and everything that calls it) never depends on those shapes.
The messages are the SDK's own objects, from either the ordinary endpoint or
the beta endpoint (used when the refusal fallback is on); both have the same
fields for what is read here.
"""

from typing import Any

from . import messages as _messages
from .... import check_types as _check_types


@_check_types.do
def message_text(message: Any) -> str:
    """All of the text blocks of *message*, joined."""
    return ''.join(block.text for block in message.content if block.type == 'text')


@_check_types.do
def tool_uses(content: list) -> list:
    """The ``tool_use`` blocks in *content*, in order."""
    return [block for block in content if block.type == 'tool_use']


@_check_types.do
def echo_content(content: list) -> list:
    """The assistant content to keep in the history and send back.

    Normally exactly what Claude produced (thinking blocks included: they
    must be returned unchanged). The exception is a turn that a fallback
    model finished after a refusal part-way through: the docs say everything
    before the last ``fallback`` marker except plain text must be left out
    (the fallback model cannot use the first model's thinking or tool calls),
    and the marker itself is only an audit note.
    """
    boundary = -1
    for index, block in enumerate(content):
        if block.type == 'fallback':
            boundary = index

    if boundary == -1:
        return list(content)

    kept = []
    for index, block in enumerate(content):
        if block.type == 'fallback':
            continue

        if index < boundary and block.type != 'text':
            continue

        kept.append(block)

    return kept


@_check_types.do
def served_by_fallback(message: Any, beta: bool) -> bool:
    """Whether a refusal-fallback model produced *message*."""
    if not beta:
        return False

    iterations = message.usage.iterations or []
    return any(entry.type == 'fallback_message' for entry in iterations)


@_check_types.do
def message_usage(message: Any, beta: bool) -> _messages.Usage:
    """Tokens used by *message*. With the refusal fallback, the per-attempt
    list is the true total (the top-level figure covers only the attempt that
    produced the returned message)."""
    usage = message.usage

    if beta and usage.iterations:
        total = _messages.Usage()
        for entry in usage.iterations:
            total = total + _usage_from(entry.model_dump())

        return total

    return _usage_from(usage.model_dump())


@_check_types.do
def _usage_from(fields: dict[str, Any]) -> _messages.Usage:
    return _messages.Usage(
        input_tokens=_count(fields.get('input_tokens')),
        output_tokens=_count(fields.get('output_tokens')),
        cache_read_tokens=_count(fields.get('cache_read_input_tokens')),
        cache_write_tokens=_count(fields.get('cache_creation_input_tokens')))


@_check_types.do
def _count(value: object) -> int:
    if isinstance(value, int):
        return value

    return 0
