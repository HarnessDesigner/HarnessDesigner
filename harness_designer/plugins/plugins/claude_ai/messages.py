# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The plain data that goes in and out: tools, usage, and the response."""

from collections.abc import Callable
from typing import Any

from dataclasses import dataclass

import json
import re

from . import models as _models
from .... import check_types as _check_types

_TOOL_NAME = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

# A tool result longer than this is cut (the model is told): a runaway
# result would use up the context window and the user's money.
MAX_TOOL_RESULT_CHARS = 60_000


@dataclass(frozen=True)
class Usage:
    """Tokens used by one or more requests."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @_check_types.do
    def __add__(self, other: 'Usage') -> 'Usage':
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens)

    @_check_types.do
    def estimated_cost(self, model_id: str) -> float | None:
        """Estimated US dollars for these tokens on *model_id*; ``None`` for
        a model whose prices are not known. An estimate: list prices only."""
        info = _models.model_info(model_id)
        if info is None:
            return None

        per_million = 1_000_000
        return (self.input_tokens * info.input_price
                + self.output_tokens * info.output_price
                + self.cache_read_tokens * info.cache_read_price
                + self.cache_write_tokens * info.input_price * _models.CACHE_WRITE_FACTOR) / per_million


@dataclass
class Tool:
    """A function Claude may ask the application to run.

    :ivar name: Letters, digits, ``_`` and ``-``; up to 64 characters.
    :ivar description: What it does and when to use it -- written for the
        model; this is the main thing that decides whether it is used well.
    :ivar input_schema: JSON Schema of the arguments (``type: object``).
    :ivar handler: Called with the arguments dict, on the worker thread.
        Return a string, or anything JSON can hold; raise to report a
        failure to the model. A tool that has to ask the user something
        uses :func:`~harness_designer.claude.qt.call_in_gui`.
    :ivar strict: Ask the API to guarantee the arguments match the schema.
        Needs a closed schema (``additionalProperties: false`` and every
        property listed in ``required``).
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], object]
    strict: bool = False

    @_check_types.do
    def __post_init__(self) -> None:
        if not _TOOL_NAME.match(self.name):
            raise ValueError(f'tool name {self.name!r} must be 1-64 letters, digits, "_" or "-"')

        if self.input_schema.get('type') != 'object':
            raise ValueError(f'tool {self.name!r}: input_schema must have "type": "object"')

        if self.strict:
            if self.input_schema.get('additionalProperties') is not False:
                raise ValueError(f'tool {self.name!r}: a strict tool needs "additionalProperties": false')

            properties = set(self.input_schema.get('properties', {}))
            if properties != set(self.input_schema.get('required', [])):
                raise ValueError(f'tool {self.name!r}: a strict tool must list every property in "required"')

    @_check_types.do
    def to_param(self) -> dict[str, Any]:
        """The tool as the API wants it."""
        param: dict[str, Any] = {
            'name': self.name,
            'description': self.description,
            'input_schema': self.input_schema}

        if self.strict:
            param['strict'] = True

        return param


@_check_types.do
def result_text(value: object) -> str:
    """A tool handler's return value as the text sent back to the model."""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, default=str)

    if len(text) > MAX_TOOL_RESULT_CHARS:
        text = text[:MAX_TOOL_RESULT_CHARS] + f'\n[result cut: {len(text) - MAX_TOOL_RESULT_CHARS} more characters]'

    return text


@dataclass
class Response:
    """What came back from a ``send()`` / ``ask()``.

    :ivar text: Everything Claude said, as text.
    :ivar data: The parsed JSON when an ``output_schema`` was given, else ``None``.
    :ivar stop_reason: Why it stopped (``end_turn``, ...).
    :ivar model: The model that produced the final answer (differs from the
        requested one when a refusal fallback served it).
    :ivar requested_model: The model that was asked.
    :ivar usage: Tokens used by every request this call made.
    :ivar request_id: The API's id for the last request (quote it to support).
    :ivar tool_calls: How many times Claude called a tool.
    :ivar rounds: How many requests the call took (more than one when tools ran).
    :ivar served_by_fallback: A refusal fallback model answered.
    """

    text: str
    data: object
    stop_reason: str
    model: str
    requested_model: str
    usage: Usage
    request_id: str | None
    tool_calls: int = 0
    rounds: int = 1
    served_by_fallback: bool = False

    @property
    @_check_types.do
    def estimated_cost(self) -> float | None:
        """Estimated US dollars this call cost (list prices)."""
        return self.usage.estimated_cost(self.requested_model)
