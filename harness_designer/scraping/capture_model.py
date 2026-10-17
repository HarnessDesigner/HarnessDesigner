# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""One request the page made, as the capture hook reported it.

Pure data: no Qt, so everything here is covered by ordinary unit tests.
"""

import json
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from . import request_code as _request_code
from .. import check_types as _check_types

# A report bigger than this is dropped: it comes from page JavaScript, which
# can send anything.
MAX_RECORD_CHARS = 12_000_000

_JSON_START = ('{', '[')


@dataclass
class CapturedRequest:
    """A finished ``fetch`` / ``XMLHttpRequest`` call.

    Response header names are lower case (that is how the page API reports
    them); request header names are as the page set them.
    """

    number: int
    kind: str
    method: str
    url: str
    status: int
    request_headers: dict[str, str]
    request_body: str | None
    request_body_kind: str
    response_headers: dict[str, str]
    response_body: str | None
    response_truncated: bool
    page_url: str
    user_agent: str
    duration_ms: int
    error: str | None
    _json: object = field(default=None, init=False, repr=False, compare=False)
    _json_checked: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    @_check_types.do
    def content_type(self) -> str:
        """The response media type, lower case, without parameters."""
        raw = self.response_headers.get('content-type', '')
        return raw.split(';', 1)[0].strip().lower()

    @property
    @_check_types.do
    def display_url(self) -> str:
        """Path and query only -- the host is nearly always the page's own."""
        split = urlsplit(self.url)
        text = split.path or '/'
        if split.query:
            text += '?' + split.query

        return text

    @property
    @_check_types.do
    def size(self) -> int:
        """Response size in bytes: the server's ``content-length`` when it
        said, otherwise the length of the body that was captured."""
        declared = self.response_headers.get('content-length', '')
        if declared.isdigit():
            return int(declared)

        if self.response_body is None:
            return 0

        return len(self.response_body.encode('utf-8', errors='replace'))

    @property
    @_check_types.do
    def is_json(self) -> bool:
        if self.parsed_json() is not None:
            return True

        return self._json_is_null

    @property
    @_check_types.do
    def is_html(self) -> bool:
        if self.content_type in ('text/html', 'application/xhtml+xml'):
            return True

        body = (self.response_body or '').lstrip()[:200].lower()
        return body.startswith('<!doctype html') or body.startswith('<html')

    @property
    @_check_types.do
    def is_xml(self) -> bool:
        return 'xml' in self.content_type and not self.is_html

    @_check_types.do
    def parsed_json(self) -> object:
        """The response body as parsed JSON, or ``None`` when it is not JSON.

        A literal JSON ``null`` also gives ``None``; use :attr:`is_json` to
        tell the two apart. Bodies are treated as JSON when the server says
        so, or when they simply look like JSON -- plenty of APIs send
        ``text/plain``.
        """
        if self._json_checked:
            return self._json

        self._json_checked = True
        body = self.response_body
        if body is None or self.response_truncated:
            return None

        looks_json = 'json' in self.content_type or body.lstrip().startswith(_JSON_START)
        if not looks_json:
            return None

        try:
            self._json = json.loads(body)
        except ValueError:
            self._json = None

        return self._json

    @property
    @_check_types.do
    def _json_is_null(self) -> bool:
        body = (self.response_body or '').strip()
        return 'json' in self.content_type and body == 'null'

    @_check_types.do
    def to_spec(self) -> _request_code.RequestSpec:
        """The request in a form :func:`request_code.generate_request_code`
        can turn into ``requests`` code.

        The browser sends ``Referer``, ``Origin`` and ``User-Agent`` itself
        without the page ever setting them, so they are added from what the
        page reported -- servers do check them.
        """
        headers = dict(self.request_headers)
        present = {name.lower() for name in headers}

        if 'referer' not in present and self.page_url:
            headers['Referer'] = self.page_url

        if 'origin' not in present and self.method not in ('GET', 'HEAD') and self.page_url:
            split = urlsplit(self.page_url)
            headers['Origin'] = f'{split.scheme}://{split.netloc}'

        if 'user-agent' not in present and self.user_agent:
            headers['User-Agent'] = self.user_agent

        return _request_code.RequestSpec(
            method=self.method,
            url=self.url,
            headers=headers,
            body=self.request_body,
            body_kind=self.request_body_kind,
            response_is_json=self.is_json)


@_check_types.do
def parse_record(text: str, number: int) -> CapturedRequest | None:
    """Turn one report from the hook into a :class:`CapturedRequest`.

    Returns ``None`` for anything that is not a well-formed report: the
    text comes from the page being browsed, so it is checked, not trusted.
    """
    if len(text) > MAX_RECORD_CHARS:
        return None

    try:
        raw = json.loads(text)
    except ValueError:
        return None

    if not isinstance(raw, dict):
        return None

    url = raw.get('url')
    method = raw.get('method')
    if not isinstance(url, str) or not isinstance(method, str):
        return None

    status = raw.get('status')
    if not isinstance(status, int):
        status = 0

    duration = raw.get('durationMs')
    if not isinstance(duration, int):
        duration = 0

    kind = raw.get('kind')
    if kind not in ('xhr', 'fetch'):
        kind = 'xhr'

    return CapturedRequest(
        number=number,
        kind=kind,
        method=method.upper(),
        url=url,
        status=status,
        request_headers=_text_dict(raw.get('requestHeaders')),
        request_body=_text_or_none(raw.get('requestBody')),
        request_body_kind=_text(raw.get('requestBodyKind')),
        response_headers={name.lower(): value for name, value in _text_dict(raw.get('responseHeaders')).items()},
        response_body=_text_or_none(raw.get('responseBody')),
        response_truncated=raw.get('responseTruncated') is True,
        page_url=_text(raw.get('pageUrl')),
        user_agent=_text(raw.get('userAgent')),
        duration_ms=duration,
        error=_text_or_none(raw.get('error')))


@_check_types.do
def describe_size(size: int) -> str:
    """``1.4 KB`` style size for the Network table."""
    if size < 1024:
        return f'{size} B'

    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'

    return f'{size / (1024 * 1024):.1f} MB'


@_check_types.do
def _text(value: object) -> str:
    if isinstance(value, str):
        return value

    return ''


@_check_types.do
def _text_or_none(value: object) -> str | None:
    if isinstance(value, str):
        return value

    return None


@_check_types.do
def _text_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    return {str(name): str(item) for name, item in value.items()}
