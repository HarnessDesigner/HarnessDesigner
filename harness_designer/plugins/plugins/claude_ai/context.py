# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""How outside knowledge gets into a conversation.

A :class:`ContextProvider` supplies pieces of background -- rules of the
domain, facts about the open project, things the user has said before --
that belong in front of Claude when a conversation starts. This is the seam
where, later, what the concentric-twisting feature has learned from the
user's decisions plugs in (see CLAUDE_API_DESIGN.md).

Providers are asked ONCE, when the conversation is created, and what they
return becomes part of its frozen system prompt. They are never asked again
for that conversation: changing the system prompt mid-conversation would
invalidate Claude's thinking and the prompt cache (use ``Conversation.note``
for anything learned later).
"""

from dataclasses import dataclass

from .... import check_types as _check_types


@dataclass(frozen=True)
class ContextBlock:
    """One titled piece of background.

    :ivar title: Short heading Claude sees above the text.
    :ivar text: The background itself.
    """

    title: str
    text: str


class ContextProvider:
    """Base class for something that can say what Claude should know."""

    @property
    @_check_types.do
    def name(self) -> str:
        """For logs and error messages."""
        return type(self).__name__

    @_check_types.do
    def blocks(self, topic: str) -> list[ContextBlock]:
        """The background relevant to *topic* (free text describing what the
        conversation is about; providers may ignore it).

        Must be deterministic for a given state: the result is part of the
        cached prompt prefix.
        """
        raise NotImplementedError


class StaticContext(ContextProvider):
    """Fixed background text, for the simple cases (and for tests)."""

    @_check_types.do
    def __init__(self, title: str, text: str) -> None:
        self._block = ContextBlock(title, text)

    @_check_types.do
    def blocks(self, topic: str) -> list[ContextBlock]:
        return [self._block]


@_check_types.do
def compose_system(system: str | None, providers: list[ContextProvider], topic: str) -> str | None:
    """The frozen system prompt: *system*, then every provider's blocks in
    the order the providers were given.

    Returns ``None`` when there is nothing to say.
    """
    parts: list[str] = []
    if system and system.strip():
        parts.append(system.strip())

    sections: list[str] = []
    for provider in providers:
        for block in provider.blocks(topic):
            if block.text.strip():
                sections.append(f'## {block.title}\n{block.text.strip()}')

    if sections:
        parts.append('# Background\n\n' + '\n\n'.join(sections))

    if not parts:
        return None

    return '\n\n'.join(parts)
