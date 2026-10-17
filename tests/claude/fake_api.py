# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A local stand-in for Anthropic's Messages API.

It speaks the real wire format -- server-sent events for a streamed message,
JSON error bodies with the right statuses -- so the real ``anthropic`` SDK
runs against it unchanged. Every request is recorded, which lets a test
assert exactly what the application would have sent. Nothing leaves the
machine and no key is spent.

Script what the server says next with :meth:`FakeAPI.queue`; build replies
with the module's ``text`` / ``tools`` / ``error`` / ``refusal`` helpers.
"""

import http.server
import json
import socketserver
import threading
import time
from dataclasses import dataclass, field


@dataclass
class Recorded:
    path: str
    headers: dict[str, str]
    body: dict


@dataclass
class Reply:
    """One scripted answer."""

    status: int = 200
    events: list[tuple[str, dict]] = field(default_factory=list)
    body: dict | None = None
    headers: dict[str, str] = field(default_factory=dict)
    event_delay: float = 0.0


def _chunks(text: str, size: int = 7) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)] or ['']


def message_events(blocks: list[tuple], stop_reason: str = 'end_turn', model: str = 'claude-opus-5-5',
                   input_tokens: int = 25, output_tokens: int = 40, message_id: str = 'msg_fake',
                   stop_details: dict | None = None, iterations: list[dict] | None = None,
                   cache_read: int = 0, cache_write: int = 0) -> list[tuple[str, dict]]:
    """The SSE events for one message. *blocks* are tuples:

    ``('text', 'hello')``, ``('thinking', 'hmm', 'sig')``,
    ``('tool', 'toolu_1', 'name', {...})``, ``('fallback', 'from', 'to')``.
    """
    usage = {'input_tokens': input_tokens, 'output_tokens': 1,
             'cache_read_input_tokens': cache_read, 'cache_creation_input_tokens': cache_write}
    events: list[tuple[str, dict]] = [('message_start', {'type': 'message_start', 'message': {
        'id': message_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': model,
        'stop_reason': None, 'stop_sequence': None, 'usage': usage}})]

    for index, block in enumerate(blocks):
        kind = block[0]
        if kind == 'text':
            events.append(('content_block_start', {'type': 'content_block_start', 'index': index,
                                                   'content_block': {'type': 'text', 'text': ''}}))
            for piece in _chunks(block[1]):
                events.append(('content_block_delta', {'type': 'content_block_delta', 'index': index,
                                                       'delta': {'type': 'text_delta', 'text': piece}}))
        elif kind == 'thinking':
            events.append(('content_block_start', {'type': 'content_block_start', 'index': index,
                                                   'content_block': {'type': 'thinking', 'thinking': '',
                                                                     'signature': ''}}))
            events.append(('content_block_delta', {'type': 'content_block_delta', 'index': index,
                                                   'delta': {'type': 'thinking_delta', 'thinking': block[1]}}))
            events.append(('content_block_delta', {'type': 'content_block_delta', 'index': index,
                                                   'delta': {'type': 'signature_delta', 'signature': block[2]}}))
        elif kind == 'tool':
            events.append(('content_block_start', {'type': 'content_block_start', 'index': index,
                                                   'content_block': {'type': 'tool_use', 'id': block[1],
                                                                     'name': block[2], 'input': {}}}))
            for piece in _chunks(json.dumps(block[3]), 11):
                events.append(('content_block_delta', {'type': 'content_block_delta', 'index': index,
                                                       'delta': {'type': 'input_json_delta', 'partial_json': piece}}))
        elif kind == 'fallback':
            events.append(('content_block_start', {'type': 'content_block_start', 'index': index,
                                                   'content_block': {'type': 'fallback', 'from': {'model': block[1]},
                                                                     'to': {'model': block[2]}}}))
        else:
            raise ValueError(kind)

        events.append(('content_block_stop', {'type': 'content_block_stop', 'index': index}))

    delta_usage = {'input_tokens': input_tokens, 'output_tokens': output_tokens,
                   'cache_read_input_tokens': cache_read, 'cache_creation_input_tokens': cache_write}
    if iterations is not None:
        delta_usage['iterations'] = iterations

    delta = {'stop_reason': stop_reason, 'stop_sequence': None}
    if stop_details is not None:
        delta['stop_details'] = stop_details

    events.append(('message_delta', {'type': 'message_delta', 'delta': delta, 'usage': delta_usage}))
    events.append(('message_stop', {'type': 'message_stop'}))
    return events


def text(answer: str, **options) -> Reply:
    return Reply(events=message_events([('text', answer)], **options))


def thinking_text(thought: str, answer: str, signature: str = 'sig-1', **options) -> Reply:
    return Reply(events=message_events([('thinking', thought, signature), ('text', answer)], **options))


def tools(*calls: tuple, thought: str | None = None, lead_in: str | None = None, **options) -> Reply:
    """A reply asking for tools: ``tools(('toolu_1', 'name', {...}), ...)``."""
    blocks: list[tuple] = []
    if thought is not None:
        blocks.append(('thinking', thought, 'sig-tool'))
    if lead_in is not None:
        blocks.append(('text', lead_in))
    for call in calls:
        blocks.append(('tool', *call))
    return Reply(events=message_events(blocks, stop_reason='tool_use', **options))


def refusal(category: str = 'cyber', explanation: str = 'Cannot help with that.') -> Reply:
    return Reply(events=message_events(
        [], stop_reason='refusal', stop_details={'type': 'refusal', 'category': category, 'explanation': explanation}))


def error(status: int, kind: str, message: str, headers: dict[str, str] | None = None) -> Reply:
    return Reply(status=status, headers=headers or {},
                 body={'type': 'error', 'error': {'type': kind, 'message': message}, 'request_id': 'req_fake'})


class _Handler(http.server.BaseHTTPRequestHandler):
    # HTTP/1.0: the response ends when the connection closes, so a stream
    # needs no chunked encoding.
    protocol_version = 'HTTP/1.0'

    def log_message(self, *args):
        pass

    def do_POST(self):
        api: FakeAPI = self.server.api
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length) or b'{}')
        headers = {name.lower(): value for name, value in self.headers.items()}

        with api.lock:
            api.requests.append(Recorded(self.path, headers, body))
            if api.script:
                reply = api.script.pop(0)
            else:
                reply = error(500, 'api_error', 'nothing was scripted for this request')

        try:
            self._send(reply, bool(body.get('stream')))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _send(self, reply: Reply, streaming: bool):
        if reply.status != 200:
            payload = json.dumps(reply.body).encode()
            self.send_response(reply.status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('request-id', 'req_fake')
            self.send_header('Content-Length', str(len(payload)))
            for name, value in reply.headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('request-id', 'req_fake_stream')
        self.send_header('Cache-Control', 'no-cache')
        for name, value in reply.headers.items():
            self.send_header(name, value)
        self.end_headers()

        for name, data in reply.events:
            self.wfile.write(f'event: {name}\ndata: {json.dumps(data)}\n\n'.encode())
            self.wfile.flush()
            if reply.event_delay:
                time.sleep(reply.event_delay)


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """Clients that hang up (a cancelled call) are not an error."""


class FakeAPI:
    """Start it, point a client's ``base_url`` at :attr:`url`, queue replies."""

    def __init__(self):
        self.requests: list[Recorded] = []
        self.script: list[Reply] = []
        self.lock = threading.Lock()
        self._server = _Server(('127.0.0.1', 0), _Handler)
        self._server.api = self
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self._server.server_address[1]}'

    def start(self) -> 'FakeAPI':
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def queue(self, *replies: Reply) -> None:
        with self.lock:
            self.script.extend(replies)

    def reset(self) -> None:
        with self.lock:
            self.requests.clear()
            self.script.clear()

    @property
    def last(self) -> Recorded:
        return self.requests[-1]
