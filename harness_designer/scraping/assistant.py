# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""What the scraper assistant says to Claude, and how it reads the answer.

No Qt and no API calls in here: this module decides what goes into a
request and what comes out of a reply, so all of it is testable. The panel
(``ui/editor_script/assistant_panel.py``) does the talking through
``harness_designer.claude``.

The rule for everything that is sent: **the user sees exactly what is going
to be sent, and nothing is silently cut.** Each piece has a size budget; a
piece that goes over is clipped with a visible marker and listed in the
report, and a script too long to send whole is refused rather than clipped
(a clipped script that Claude then "improves" and the user replaces would
lose the end of their work).
"""

from dataclasses import dataclass, field

import difflib
import json
import re

from . import capture_model as _capture_model
from .. import check_types as _check_types

MODE_EDIT = 'edit'
MODE_ANSWER = 'answer'

# Budgets, in characters (about 3 characters per token for code and markup).
MAX_SCRIPT_CHARS = 60_000
MAX_EDITOR_SELECTION_CHARS = 8_000
MAX_SOURCE_SELECTION_CHARS = 4_000
SOURCE_CONTEXT_CHARS = 1_500
MAX_REQUEST_BODY_CHARS = 4_000
MAX_RESPONSE_CHARS = 8_000
MAX_PAGE_CHARS = 40_000
# Every piece may be sent at once and the script alone can be 60,000 characters;
# past this total the user is asked to turn something off (about 33,000 tokens).
MAX_TOTAL_CHARS = 100_000
CHARS_PER_TOKEN = 3

# Shown to Claude in place of a header value that must not leave the machine.
_SECRET_HEADERS = frozenset({'cookie', 'authorization', 'proxy-authorization', 'set-cookie'})

SYSTEM_PROMPT = '''You are the scraping assistant inside Harness Designer, a desktop application. The user is building a Python web scraper with the application's built-in browser and script editor, and you help them design, write and fix the script.

## The environment the script runs in
- Python 3.11, run as a plain file from top to bottom.
- Third-party packages available: requests, beautifulsoup4 (import bs4) and lxml. Everything else must come from the standard library. Do not use selenium, playwright, scrapy, pandas, or anything not listed.

## What you are given
Each message from the user may contain labelled sections:
- <script>: the script as it is right now. Always treat this as the current version, whatever you wrote earlier.
- <selected_in_editor>: the part of the script the user has selected.
- <page_url>: the page open in the built-in browser.
- <selected_in_page_source>: text the user selected in the page's HTML source, with the text around it. The selection is between <<<SELECTED and SELECTED>>>.
- <request>: a network request the user picked (an XHR / fetch call the page made) with its response. JSON responses are shown as a digest: long lists are cut and strings shortened.
- <page_source>: the start of the page's HTML.
- <task>: what the user wants now.
Sections the user did not include are simply absent. Do not assume anything about a page you were not shown.

## Test before you answer
You have tools that run against the real page and the picked response: find_text, test_css_selector, test_xpath and inspect_json. Use them to check every selector, path and string you are about to put in the script. If a tool reports that there is no page or response, say so plainly and ask the user to load or pick one; never invent selectors for markup you have not seen.

## How to write the code
- Prefer the site's own JSON (XHR / fetch) endpoint over scraping HTML whenever the user has shown you one.
- Use CSS selectors with BeautifulSoup(html, 'lxml') or XPath with lxml.html; avoid regular expressions on HTML unless that is the only option.
- Always pass timeout= to requests, send a realistic User-Agent header, call raise_for_status(), and sleep briefly between repeated requests.
- Never put passwords, API keys, tokens or cookies in the script. If a site needs a login, read the value from an environment variable or ask the user to paste it into a clearly marked variable at the top.
- Fail loudly: no bare except, no swallowing errors. If a selector finds nothing, let it raise or report it.
- Keep the user's existing structure and variable names. Change only what the task needs.

## How to answer
- Be brief. Explain what you changed or found in a few sentences.
- When the task is marked as an edit, finish with ONE complete, runnable script in a single ```python code block (the whole file, not a fragment), so the user can replace their script with it.
- When the task is marked as a question, answer it; include code only if it helps, and do not rewrite the whole script.
- If you are unsure what the user wants, ask one short question instead of guessing.'''

# The order sections appear in the message.
_ORDER = ('script', 'script_selection', 'page_url', 'source_selection', 'request', 'page_source')


@dataclass(frozen=True)
class CodeBlock:
    """A fenced code block from a reply."""

    language: str
    code: str

    @property
    @_check_types.do
    def is_python(self) -> bool:
        return self.language in ('python', 'py', 'python3', '')


@dataclass(frozen=True)
class ItemInfo:
    """One piece of context the user may choose to send.

    :ivar id: Stable key (``script``, ``source_selection``, ...).
    :ivar title: Label for the checkbox.
    :ivar available: There is something to send.
    :ivar default: Checked when it first becomes available.
    :ivar note: Why it is unavailable, or a size warning.
    """

    id: str
    title: str
    available: bool
    default: bool
    note: str = ''


@dataclass(frozen=True)
class SectionReport:
    """What one included piece contributed to the message."""

    id: str
    title: str
    chars: int
    clipped_chars: int = 0


@dataclass
class AssembledMessage:
    """The user turn that will be sent, and the numbers about it."""

    text: str
    reports: list[SectionReport] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    @_check_types.do
    def chars(self) -> int:
        return len(self.text)

    @property
    @_check_types.do
    def estimated_tokens(self) -> int:
        return estimate_tokens(len(self.text))

    @property
    @_check_types.do
    def ok(self) -> bool:
        """Whether it may be sent."""
        return not self.problems


class AssistantContext:
    """What the assistant can learn about the page the user is working on.
    The inspector implements this. ``page_source`` and ``selected_request``
    are also called from the tools' worker thread, so they may only read
    plain Python state; ``page_url`` and ``source_selection`` are called on
    the GUI thread only and may look at widgets."""

    @_check_types.do
    def page_url(self) -> str:
        """The URL open in the browser, or ``''``."""
        raise NotImplementedError

    @_check_types.do
    def page_source(self) -> str | None:
        """The HTML source being shown, or ``None``."""
        raise NotImplementedError

    @_check_types.do
    def source_selection(self) -> tuple[str, int, int] | None:
        """(document, start, end) of the text selected in the source view,
        offsets into that document; ``None`` if nothing is selected."""
        raise NotImplementedError

    @_check_types.do
    def selected_request(self) -> _capture_model.CapturedRequest | None:
        """The network request picked in the inspector, or ``None``."""
        raise NotImplementedError


class EmptyContext(AssistantContext):
    """No page, no selection: what the assistant sees with no browser open."""

    @_check_types.do
    def page_url(self) -> str:
        return ''

    @_check_types.do
    def page_source(self) -> str | None:
        return None

    @_check_types.do
    def source_selection(self) -> tuple[str, int, int] | None:
        return None

    @_check_types.do
    def selected_request(self) -> _capture_model.CapturedRequest | None:
        return None


@_check_types.do
def estimate_tokens(chars: int) -> int:
    """A rough token count for *chars* characters of code / markup."""
    return -(-chars // CHARS_PER_TOKEN)


@_check_types.do
def clip(text: str, limit: int) -> tuple[str, int]:
    """*text* cut to *limit* characters with a visible marker, and how many
    characters were left out (0 when it fit)."""
    if len(text) <= limit:
        return text, 0

    omitted = len(text) - limit
    return text[:limit] + f'\n[... {omitted} more characters not sent ...]', omitted


@_check_types.do
def excerpt_around(document: str, start: int, end: int, context: int) -> str:
    """The selected text with *context* characters either side, the
    selection marked ``<<<SELECTED`` ... ``SELECTED>>>``."""
    left = max(0, start - context)
    right = min(len(document), end + context)

    before = document[left:start]
    after = document[end:right]
    if left > 0:
        before = '[...]' + before
    if right < len(document):
        after = after + '[...]'

    selected, _omitted = clip(document[start:end], MAX_SOURCE_SELECTION_CHARS)
    return f'{before}<<<SELECTED{selected}SELECTED>>>{after}'


@_check_types.do
def json_digest(value: object, *, max_depth: int = 6, max_items: int = 2, max_keys: int = 40,
                max_string: int = 80) -> str:
    """A short JSON outline of *value* for Claude: lists are cut to their
    first few items (with a note of how many were left out), objects keep
    their first keys, long strings are shortened, deep nesting is folded.
    Cheap to send and still shows the shape of the data."""
    reduced = _reduce(value, max_depth, max_items, max_keys, max_string)
    return json.dumps(reduced, indent=2, ensure_ascii=False)


@_check_types.do
def _reduce(value: object, depth: int, max_items: int, max_keys: int, max_string: int) -> object:
    if isinstance(value, str):
        if len(value) > max_string:
            return value[:max_string] + f'... ({len(value) - max_string} more characters)'

        return value

    if isinstance(value, dict):
        if depth <= 0:
            return f'{{... {len(value)} keys}}'

        reduced: dict[str, object] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_keys:
                reduced['...'] = f'{len(value) - max_keys} more keys'
                break

            reduced[str(key)] = _reduce(item, depth - 1, max_items, max_keys, max_string)

        return reduced

    if isinstance(value, list):
        if depth <= 0:
            return f'[... {len(value)} items]'

        shown = [_reduce(item, depth - 1, max_items, max_keys, max_string) for item in value[:max_items]]
        if len(value) > max_items:
            shown.append(f'... {len(value) - max_items} more items (of {len(value)} in total)')

        return shown

    return value


@_check_types.do
def extract_code_blocks(reply: str) -> list[CodeBlock]:
    """Every fenced code block in *reply*, in order."""
    blocks: list[CodeBlock] = []
    for found in _FENCE.finditer(reply):
        blocks.append(CodeBlock(found.group(1).lower(), found.group(2).rstrip('\n')))

    return blocks


_FENCE = re.compile(r'^```[ \t]*([\w+.-]*)[^\n]*\n(.*?)^```[ \t]*$', re.S | re.M)


@_check_types.do
def proposed_script(blocks: list[CodeBlock]) -> CodeBlock | None:
    """The block most likely to be the complete script: the last Python
    block (replies end with it)."""
    python = [block for block in blocks if block.is_python]
    if not python:
        return None

    return python[-1]


@_check_types.do
def unified_diff(old: str, new: str) -> list[str]:
    """Lines of a unified diff from *old* to *new* (empty if identical)."""
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(), 'your script', 'proposed script', lineterm=''))


@_check_types.do
def list_items(context: AssistantContext, script: str, script_selection: str) -> list[ItemInfo]:
    """What can be sent right now, in the order it will appear."""
    items: list[ItemInfo] = []

    if not script.strip():
        items.append(ItemInfo('script', 'The script in the editor', False, True, 'The script is empty.'))
    elif len(script) > MAX_SCRIPT_CHARS:
        items.append(ItemInfo(
            'script', 'The script in the editor', False, True,
            f'Too long to send whole ({len(script):,} characters; the limit is {MAX_SCRIPT_CHARS:,}). '
            'Select the part you want help with instead.'))
    else:
        items.append(ItemInfo('script', 'The script in the editor', True, True))

    if script_selection.strip():
        items.append(ItemInfo('script_selection', 'The text selected in the editor', True, True))
    else:
        items.append(ItemInfo('script_selection', 'The text selected in the editor', False, True,
                              'Nothing is selected in the editor.'))

    if context.page_url():
        items.append(ItemInfo('page_url', 'The address of the open page', True, True))
    else:
        items.append(ItemInfo('page_url', 'The address of the open page', False, True, 'No page is open.'))

    if context.source_selection() is not None:
        items.append(ItemInfo('source_selection', 'The text selected in the page source (with what surrounds it)',
                              True, True))
    else:
        items.append(ItemInfo('source_selection', 'The text selected in the page source (with what surrounds it)',
                              False, True, 'Nothing is selected in the Source tab.'))

    if context.selected_request() is not None:
        items.append(ItemInfo('request', 'The network request selected in the inspector, with its response',
                              True, True))
    else:
        items.append(ItemInfo('request', 'The network request selected in the inspector, with its response',
                              False, True, 'No request is selected.'))

    source = context.page_source()
    if source:
        note = f'{len(source):,} characters; only the first {MAX_PAGE_CHARS:,} are sent.'
        items.append(ItemInfo('page_source', 'The start of the page source', True, False, note))
    else:
        items.append(ItemInfo('page_source', 'The start of the page source', False, False, 'No source is loaded.'))

    return items


@_check_types.do
def assemble(task: str, mode: str, enabled: set[str], context: AssistantContext, script: str,
             script_selection: str) -> AssembledMessage:
    """The user turn for *task*: the chosen pieces of context, then the task.

    Pieces that are switched on but not available are left out (and are
    not an error: the panel shows why they are unavailable).
    """
    available = {item.id for item in list_items(context, script, script_selection) if item.available}
    parts: list[str] = []
    reports: list[SectionReport] = []

    for item_id in _ORDER:
        if item_id not in enabled or item_id not in available:
            continue

        title, body, clipped = _section(item_id, context, script, script_selection)
        parts.append(f'<{_TAGS[item_id]}>\n{body}\n</{_TAGS[item_id]}>')
        reports.append(SectionReport(item_id, title, len(body), clipped))

    if mode == MODE_EDIT:
        parts.append('<task mode="edit">\n' + task.strip() + '\n</task>')
    else:
        parts.append('<task mode="question">\n' + task.strip() + '\n</task>')

    message = AssembledMessage('\n\n'.join(parts), reports)

    if not task.strip():
        message.problems.append('Type what you want first.')

    if message.chars > MAX_TOTAL_CHARS:
        message.problems.append(
            f'Too much to send at once ({message.chars:,} characters; the limit is {MAX_TOTAL_CHARS:,}). '
            'Turn something off.')

    return message


_TAGS = {
    'script': 'script',
    'script_selection': 'selected_in_editor',
    'page_url': 'page_url',
    'source_selection': 'selected_in_page_source',
    'request': 'request',
    'page_source': 'page_source'}


@_check_types.do
def _section(item_id: str, context: AssistantContext, script: str, script_selection: str) -> tuple[str, str, int]:
    """(title, body, characters clipped) for one piece of context."""
    if item_id == 'script':
        return 'script', script, 0

    if item_id == 'script_selection':
        body, clipped = clip(script_selection, MAX_EDITOR_SELECTION_CHARS)
        return 'selected in editor', body, clipped

    if item_id == 'page_url':
        return 'page url', context.page_url(), 0

    if item_id == 'source_selection':
        document, start, end = context.source_selection()
        body = excerpt_around(document, start, end, SOURCE_CONTEXT_CHARS)
        return 'selected in page source', body, max(0, (end - start) - MAX_SOURCE_SELECTION_CHARS)

    if item_id == 'request':
        return 'network request', request_summary(context.selected_request()), 0

    body, clipped = clip(context.page_source() or '', MAX_PAGE_CHARS)
    return 'page source', body, clipped


@_check_types.do
def request_summary(request: _capture_model.CapturedRequest) -> str:
    """A captured request as text for Claude: the call, then the response.
    Secret request headers are named but their values are not sent; JSON
    responses are digested, other text is clipped."""
    lines = [f'{request.method} {request.url}', f'status: {request.status or "failed"}']
    if request.error:
        lines.append(f'error: {request.error}')

    if request.request_headers:
        lines.append('request headers set by the page:')
        for name, value in request.request_headers.items():
            if name.lower() in _SECRET_HEADERS:
                lines.append(f'  {name}: [omitted - secret]')
            else:
                lines.append(f'  {name}: {value}')

    if request.request_body:
        body, _omitted = clip(request.request_body, MAX_REQUEST_BODY_CHARS)
        lines.append('request body:')
        lines.append(body)

    lines.append(f'response content-type: {request.content_type or "unknown"}')
    if request.response_body is None:
        lines.append('response body: (not captured: binary, empty or unreadable)')
    elif request.is_json:
        digest, _omitted = clip(json_digest(request.parsed_json()), MAX_RESPONSE_CHARS)
        lines.append('response body (JSON digest - lists and long strings are shortened):')
        lines.append(digest)
    else:
        body, _omitted = clip(request.response_body, MAX_RESPONSE_CHARS)
        lines.append('response body:')
        lines.append(body)

    return '\n'.join(lines)
