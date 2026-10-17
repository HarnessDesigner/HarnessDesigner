# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Turns a request the browser made (usually an XHR/fetch call found in the
Network tab) into the ``requests`` code that makes the same call.

The point of finding an XHR is that the script can call it directly instead
of loading and parsing the page, so this is the first snippet most
scrapers want.

Secrets are never copied into the code. ``Cookie`` and ``Authorization``
(and anything else that identifies a login) are left out and the snippet
says so, rather than writing a session into a script the user may share.
"""

import json
import pprint
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from . import snippets as _snippets
from .. import check_types as _check_types

# Headers that are worth repeating: they change what the server returns.
_KEPT_HEADERS = frozenset({
    'accept', 'accept-language', 'content-type', 'origin', 'referer', 'user-agent', 'x-requested-with'})

# Never copied into code.
_SECRET_HEADERS = frozenset({'cookie', 'authorization', 'proxy-authorization'})

_DEFAULT_TIMEOUT_SECONDS = 30


@dataclass
class RequestSpec:
    """A captured request.

    :ivar method: ``GET``, ``POST``...
    :ivar url: Full URL including the query string.
    :ivar headers: Request headers as the browser sent them.
    :ivar body: Request body as text, if it had one.
    :ivar body_kind: ``'multipart'`` when the page sent a ``FormData`` and
        ``'urlencoded'`` for a ``URLSearchParams`` (in both cases the body
        text is the fields written urlencoded), otherwise empty.
    :ivar response_is_json: The response looked like JSON, so the code
        also calls ``.json()``.
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    body_kind: str = ''
    response_is_json: bool = False


@_check_types.do
def generate_page_load(url: str, *, user_agent: str = '', doc_name: str = 'html',
                       taken: set[str] | None = None) -> _snippets.Snippet:
    """Code that downloads *url* into the variable *doc_name* -- the line
    every source-text snippet needs to have run before it."""
    headers: dict[str, str] = {}
    if user_agent:
        headers['User-Agent'] = user_agent

    spec = RequestSpec(method='GET', url=url, headers=headers)
    snippet = generate_request_code(spec, taken=taken, text_name=doc_name)
    snippet.description = f'Download {urlsplit(url).netloc}{urlsplit(url).path} into {doc_name}'
    return snippet


@_check_types.do
def generate_request_code(spec: RequestSpec, *, taken: set[str] | None = None,
                          text_name: str | None = None) -> _snippets.Snippet:
    """``requests`` code that repeats *spec*.

    With *text_name* the code also stores the response text in that
    variable (``html = response.text``), which is what the source-text
    snippets expect to find.
    """
    names = _snippets.Names(taken)
    response_name = names.new('response')

    split = urlsplit(spec.url)
    base_url = urlunsplit((split.scheme, split.netloc, split.path, '', ''))
    query = parse_qsl(split.query, keep_blank_values=True)

    kept, omitted = _split_headers(spec.headers)
    warnings: list[str] = []
    if omitted:
        warnings.append(
            'Left out ' + ', '.join(sorted(omitted)) + ': the site may need a login or session. '
            'Add the value yourself (preferably read from a file or environment variable, not typed '
            'into the script).')

    method = spec.method.upper()
    lines: list[str] = []
    arguments: list[str] = []

    url_name = names.new('url')
    lines.append(f'{url_name} = {_snippets.python_literal(base_url)}')
    arguments.append(url_name)

    if query:
        params_name = names.new('params')
        lines.append(f'{params_name} = {_format_pairs(query)}')
        arguments.append(f'params={params_name}')

    if kept:
        headers_name = names.new('headers')
        lines.append(f'{headers_name} = {_format_value(kept)}')
        arguments.append(f'headers={headers_name}')

    body_argument = _body_argument(spec, names, lines)
    if body_argument:
        arguments.append(body_argument)

    arguments.append(f'timeout={_DEFAULT_TIMEOUT_SECONDS}')

    function = method.lower()
    if function in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
        call = f'requests.{function}({", ".join(arguments)})'
    else:
        call = f'requests.request({_snippets.python_literal(method)}, {", ".join(arguments)})'

    lines.append(f'{response_name} = {call}')
    lines.append(f'{response_name}.raise_for_status()')

    result = response_name
    if spec.response_is_json:
        data_name = names.new('data')
        lines.append(f'{data_name} = {response_name}.json()')
        result = data_name

    if text_name is not None:
        lines.append(f'{text_name} = {response_name}.text')
        result = text_name

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Repeat the {method} request to {split.netloc}{split.path}',
        imports=['import requests'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def _split_headers(headers: dict[str, str]) -> tuple[dict[str, str], set[str]]:
    """The headers to write into the code, and the secret ones left out."""
    kept: dict[str, str] = {}
    omitted: set[str] = set()

    for name, value in headers.items():
        lowered = name.lower()
        if lowered in _SECRET_HEADERS:
            omitted.add(name)
        elif lowered in _KEPT_HEADERS or lowered.startswith('x-'):
            kept[name] = value

    return kept, omitted


@_check_types.do
def _body_argument(spec: RequestSpec, names: _snippets.Names, lines: list[str]) -> str:
    """The keyword argument carrying the request body, appending whatever
    assignment it needs to *lines*. Empty when there is no body."""
    if not spec.body:
        return ''

    content_type = ''
    for name, value in spec.headers.items():
        if name.lower() == 'content-type':
            content_type = value.lower()

    if 'json' in content_type:
        try:
            parsed = json.loads(spec.body)
        except ValueError:
            parsed = None

        if parsed is not None:
            payload_name = names.new('payload')
            lines.append(f'{payload_name} = {_format_value(parsed)}')
            return f'json={payload_name}'

    if spec.body_kind == 'multipart':
        # `files` with (None, value) tuples is how requests sends plain
        # fields as multipart/form-data.
        fields = {key: (None, value) for key, value in parse_qsl(spec.body, keep_blank_values=True)}
        files_name = names.new('files')
        lines.append(f'{files_name} = {_format_value(fields)}')
        return f'files={files_name}'

    # A URLSearchParams body is sent urlencoded without the page ever
    # setting a Content-Type, so the hook reports it as its own kind.
    if 'x-www-form-urlencoded' in content_type or spec.body_kind == 'urlencoded':
        pairs = parse_qsl(spec.body, keep_blank_values=True)
        form_name = names.new('form')
        lines.append(f'{form_name} = {_format_pairs(pairs)}')
        return f'data={form_name}'

    body_name = names.new('body')
    lines.append(f'{body_name} = {_snippets.python_literal(spec.body)}')
    return f'data={body_name}'


@_check_types.do
def _format_pairs(pairs: list[tuple[str, str]]) -> str:
    """A dict when every key is unique, otherwise the list of pairs that
    ``requests`` also accepts (it keeps repeated keys)."""
    keys = [key for key, _value in pairs]
    if len(set(keys)) == len(keys):
        return _format_value(dict(pairs))

    return _format_value(pairs)


@_check_types.do
def _format_value(value: object) -> str:
    return pprint.pformat(value, sort_dicts=False, width=88)
