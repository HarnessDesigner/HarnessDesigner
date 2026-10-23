# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The tools the scraper assistant may call: ways for Claude to check a
selector, a string or a JSON path against the REAL page the user is looking
at, instead of guessing.

All read-only and all on in-memory text. Deliberately absent: a regular
expression tester. A model-written regex can backtrack catastrophically, and
a Python ``re`` call cannot be interrupted, so it would hang the worker
thread for good; CSS selectors, XPath and plain text search cannot.

Each handler runs on the worker thread and may be called while the user
keeps clicking, so everything is looked up through the context at call time
(the tool definitions themselves never change: a conversation's tools are
fixed when it starts).
"""

from collections.abc import Callable
from typing import Any

import bs4
import lxml.etree
import lxml.html
import soupsieve

from . import assistant as _assistant
from .. import check_types as _check_types
from ..plugins.plugins import claude_ai as _claude

# How much of each match the model is shown.
MAX_MATCHES = 5
MAX_TEXT_CHARS = 200
MAX_HTML_CHARS = 300
MAX_ATTRIBUTES = 8
FIND_CONTEXT_CHARS = 80
MAX_JSON_CHARS = 4_000

_DOCUMENTS = ('page', 'response')

_DOCUMENT_PROPERTY = {
    'type': 'string',
    'enum': list(_DOCUMENTS),
    'description': '"page" is the HTML source shown in the Source tab; "response" is the response body of the '
                   'network request the user selected.'}


class _ParseCache:
    """Remembers the last few parsed documents (parsing a large page is
    slow, and a model often tests several selectors on the same one)."""

    @_check_types.do
    def __init__(self, parse: Callable[[str], Any], size: int = 4):
        self._parse = parse
        self._size = size
        self._entries: list[tuple[str, Any]] = []

    @_check_types.do
    def get(self, text: str) -> Any:
        for cached_text, parsed in self._entries:
            if cached_text is text or cached_text == text:
                return parsed

        parsed = self._parse(text)
        self._entries.insert(0, (text, parsed))
        del self._entries[self._size:]
        return parsed


_SOUPS = _ParseCache(lambda text: bs4.BeautifulSoup(text, 'lxml'))
_TREES = _ParseCache(lambda text: lxml.html.fromstring(text))


@_check_types.do
def document_text(context: _assistant.AssistantContext, which: str) -> str:
    """The text of the named document.

    :raises ValueError: There is no such document right now (the message
        goes back to the model, which should tell the user).
    """
    if which == 'page':
        text = context.page_source()
        if not text:
            raise ValueError('There is no page source loaded. Ask the user to open a page in the browser.')

        return text

    if which == 'response':
        request = context.selected_request()
        if request is None:
            raise ValueError('No network request is selected. Ask the user to select one in the Network tab.')

        if request.response_body is None:
            raise ValueError('The selected request has no readable text response.')

        return request.response_body

    raise ValueError(f'document must be one of: {", ".join(_DOCUMENTS)}')


@_check_types.do
def find_text(text: str, needle: str) -> dict[str, Any]:
    """Where *needle* occurs in *text*."""
    if not needle:
        raise ValueError('text must not be empty')

    positions: list[int] = []
    index = text.find(needle)
    while index != -1:
        positions.append(index)
        index = text.find(needle, index + len(needle))

    matches = []
    for position in positions[:MAX_MATCHES]:
        left = max(0, position - FIND_CONTEXT_CHARS)
        right = min(len(text), position + len(needle) + FIND_CONTEXT_CHARS)
        matches.append({'offset': position, 'context': text[left:right]})

    return {'count': len(positions), 'shown': len(matches), 'matches': matches}


@_check_types.do
def run_css(text: str, selector: str) -> dict[str, Any]:
    """The elements *selector* matches in the HTML *text* (parsed with
    ``lxml`` through BeautifulSoup, as the generated code does)."""
    soup = _SOUPS.get(text)
    try:
        found = soup.select(selector)
    except (soupsieve.SelectorSyntaxError, ValueError) as error:
        raise ValueError(f'invalid CSS selector: {error}') from error

    matches = []
    for element in found[:MAX_MATCHES]:
        attributes = {}
        for name, value in list(element.attrs.items())[:MAX_ATTRIBUTES]:
            attributes[name] = value
        matches.append({
            'tag': element.name,
            'text': element.get_text(' ', strip=True)[:MAX_TEXT_CHARS],
            'attributes': attributes,
            'html': str(element)[:MAX_HTML_CHARS]})

    return {'count': len(found), 'shown': len(matches), 'matches': matches}


@_check_types.do
def run_xpath(text: str, expression: str) -> dict[str, Any]:
    """What the XPath *expression* selects in the HTML *text*."""
    tree = _TREES.get(text)
    try:
        found = tree.xpath(expression)
    except lxml.etree.XPathError as error:
        raise ValueError(f'invalid XPath: {error}') from error

    if not isinstance(found, list):
        return {'count': 1, 'shown': 1, 'matches': [{'value': str(found)[:MAX_TEXT_CHARS]}]}

    matches = []
    for node in found[:MAX_MATCHES]:
        if isinstance(node, lxml.html.HtmlElement):
            matches.append({
                'tag': str(node.tag),
                'text': ' '.join(node.text_content().split())[:MAX_TEXT_CHARS],
                'attributes': dict(list(node.attrib.items())[:MAX_ATTRIBUTES]),
                'html': lxml.html.tostring(node, encoding='unicode')[:MAX_HTML_CHARS]})
        else:
            matches.append({'value': str(node)[:MAX_TEXT_CHARS]})

    return {'count': len(found), 'shown': len(matches), 'matches': matches}


@_check_types.do
def lookup_json(value: object, path: list[str | int]) -> dict[str, Any]:
    """The part of *value* at *path* (keys and list indexes), shown as a
    digest if it is large."""
    current = value
    for step in path:
        try:
            current = current[step]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f'nothing at {path!r}: {step!r} does not exist there ({type(error).__name__})') from error

    text = _assistant.json_digest(current)
    clipped, _omitted = _assistant.clip(text, MAX_JSON_CHARS)
    return {'path': path, 'type': type(current).__name__, 'value': clipped}


@_check_types.do
def make_tools(get_context: Callable[[], _assistant.AssistantContext | None]) -> list[_claude.Tool]:
    """The assistant's tools, reading the page through *get_context* at the
    moment they are called."""

    @_check_types.do
    def context() -> _assistant.AssistantContext:
        current = get_context()
        if current is None:
            return _assistant.EmptyContext()

        return current

    @_check_types.do
    def do_find_text(arguments: dict[str, Any]) -> dict[str, Any]:
        return find_text(document_text(context(), arguments['document']), arguments['text'])

    @_check_types.do
    def do_css(arguments: dict[str, Any]) -> dict[str, Any]:
        return run_css(document_text(context(), arguments['document']), arguments['selector'])

    @_check_types.do
    def do_xpath(arguments: dict[str, Any]) -> dict[str, Any]:
        return run_xpath(document_text(context(), arguments['document']), arguments['xpath'])

    @_check_types.do
    def do_json(arguments: dict[str, Any]) -> dict[str, Any]:
        request = context().selected_request()
        if request is None:
            raise ValueError('No network request is selected. Ask the user to select one in the Network tab.')

        if not request.is_json:
            raise ValueError('The selected request\'s response is not JSON.')

        return lookup_json(request.parsed_json(), list(arguments.get('path', [])))

    return [
        _claude.Tool(
            'find_text',
            'Find where a piece of text occurs in the page source or the selected response. Returns how many '
            'times it occurs and the surrounding text of the first few. Use it to confirm a string exists '
            'exactly as you intend to write it.',
            {'type': 'object', 'properties': {
                'document': _DOCUMENT_PROPERTY,
                'text': {'type': 'string', 'description': 'The exact text to look for (case-sensitive).'}},
             'required': ['document', 'text']},
            do_find_text),
        _claude.Tool(
            'test_css_selector',
            'Run a CSS selector against the page source or the selected response, parsed with BeautifulSoup '
            'and the lxml parser exactly as the script will do. Returns how many elements match and, for the '
            'first few, their tag, text, attributes and HTML.',
            {'type': 'object', 'properties': {
                'document': _DOCUMENT_PROPERTY,
                'selector': {'type': 'string', 'description': 'A CSS selector, e.g. "div.item > span.price".'}},
             'required': ['document', 'selector']},
            do_css),
        _claude.Tool(
            'test_xpath',
            'Run an XPath expression against the page source or the selected response, parsed with '
            'lxml.html. Returns how many nodes it selects and, for the first few, their tag, text, '
            'attributes and HTML (or the value, for attributes and text nodes).',
            {'type': 'object', 'properties': {
                'document': _DOCUMENT_PROPERTY,
                'xpath': {'type': 'string', 'description': 'An XPath 1.0 expression, e.g. "//a[@class=\'buy\']/@href".'}},
             'required': ['document', 'xpath']},
            do_xpath),
        _claude.Tool(
            'inspect_json',
            'Look at the part of the selected JSON response found by following a path of keys and list '
            'indexes from the top. Use an empty path for the top level. Large values are shown as a digest.',
            {'type': 'object', 'properties': {
                'path': {'type': 'array', 'items': {'type': ['string', 'integer']},
                         'description': 'Keys (strings) and list indexes (integers), e.g. ["items", 0, "price"].'}},
             'required': ['path']},
            do_json)]
