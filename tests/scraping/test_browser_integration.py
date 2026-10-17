# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The real browser (QtWebEngine, headless) against a local web server:
capture of fetch / XHR traffic, the page source in both modes, popups,
element picking, and the whole panel from a loaded page to a runnable
script.

Everything stays on 127.0.0.1; the browser never reaches the internet.
"""

import contextlib
import http.server
import json
import socketserver
import sys
import threading
import types
import unittest

from tests import _bootstrap
from tests.scraping import sample_pages  # noqa: F401  (keeps the package importable)

APP = _bootstrap.make_app()

from PySide6 import QtCore, QtTest, QtWidgets  # noqa: E402

browser_widget = _bootstrap.load('ui.web_viewer.browser_widget')
browser_dock = _bootstrap.load('ui.web_viewer.browser_dock')
browser_pick = _bootstrap.load('scraping.browser_pick')

PAGE = b'''<!doctype html><html><head><title>Scraper test</title></head><body>
<h1 id="title">Shop</h1>
<div class="item"><span class="price">$9.99</span></div>
<div class="item"><span class="price">$19.99</span> <a class="buy" href="/buy/2">Buy</a></div>
<div id="static">served by the server</div><div id="js"></div>
<a id="popup" target="_blank" href="/page2">second page</a>
<script>
document.getElementById('js').textContent = ['rendered', 'by', 'script'].join(' ');
fetch('/api/items?page=1', {headers: {'X-Requested-With': 'fetch', 'Accept': 'application/json'}})
  .then(function (r) { return r.json(); })
  .then(function (d) { document.title = 'fetched ' + d.items.length; });
var x = new XMLHttpRequest();
x.open('POST', '/api/search');
x.setRequestHeader('Content-Type', 'application/json');
x.send(JSON.stringify({q: 'bolt', n: 3}));
var y = new XMLHttpRequest();
y.open('GET', '/fragment');
y.send();
var form = new FormData(); form.append('a', '1'); form.append('b', 'two words');
fetch('/api/form', {method: 'POST', body: form});
fetch('/api/form', {method: 'POST', body: new URLSearchParams({c: '3', d: 'four words'})});
fetch('/image.png').then(function (r) { return r.blob(); });
</script></body></html>'''

PAGE2 = b'<!doctype html><html><head><title>Second</title></head><body><p>two</p></body></html>'
FRAGMENT = b'<ul><li class="hit">alpha</li><li class="hit">beta</li></ul>'
PNG = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f0300'
                    '0505ff0c5d9ed10000000049454e44ae426082')


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, body: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/':
            self.reply(PAGE, 'text/html; charset=utf-8')
        elif path == '/page2':
            self.reply(PAGE2, 'text/html; charset=utf-8')
        elif path == '/fragment':
            self.reply(FRAGMENT, 'text/html; charset=utf-8')
        elif path == '/image.png':
            self.reply(PNG, 'image/png')
        elif path == '/api/items':
            body = json.dumps({'items': [{'name': 'Widget', 'price': 9.99}, {'name': 'Gadget', 'price': 19.99}]})
            self.reply(body.encode(), 'application/json')
        else:
            self.reply(b'not found', 'text/plain', 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        if self.path == '/api/search':
            self.reply(json.dumps({'echo': json.loads(data), 'ok': True}).encode(), 'application/json')
        else:
            self.reply(json.dumps({'ok': True}).encode(), 'application/json')


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """The browser drops connections when a test ends; that is not an error."""


SERVER = None
BASE = ''


def setUpModule():
    global SERVER, BASE
    SERVER = Server(('127.0.0.1', 0), Handler)
    BASE = f'http://127.0.0.1:{SERVER.server_address[1]}'
    threading.Thread(target=SERVER.serve_forever, daemon=True).start()


def tearDownModule():
    SERVER.shutdown()
    SERVER.server_close()


def wait_until(predicate, timeout: float = 25.0, what: str = 'the browser') -> None:
    waited = 0.0
    while not predicate():
        QtTest.QTest.qWait(25)
        waited += 0.025
        if waited > timeout:
            raise AssertionError(f'timed out waiting for {what}')


def run_js(page, script: str):
    """Run *script* in the page and return its result."""
    result = []
    page.runJavaScript(script, result.append)
    wait_until(lambda: result, what='a script result')
    return result[0]


@contextlib.contextmanager
def no_network(document: str = '', json_value: object = None):
    original = sys.modules.get('requests')
    calls = []

    def make(verb):
        def call(*args, **kwargs):
            calls.append((verb, args, kwargs))
            return types.SimpleNamespace(raise_for_status=lambda: None, text=document, json=lambda: json_value)
        return call

    sys.modules['requests'] = types.SimpleNamespace(get=make('get'), post=make('post'), request=make('request'))
    try:
        yield calls
    finally:
        if original is None:
            del sys.modules['requests']
        else:
            sys.modules['requests'] = original


class BrowserTests(unittest.TestCase):
    EXPECTED_REQUESTS = 6

    def setUp(self):
        self.browser = browser_widget.BrowserWidget(None)
        self.browser.resize(900, 650)
        self.browser.show()
        self.captured = []
        self.sources = []
        self.messages = []
        self.browser.requestCaptured.connect(self.captured.append)
        self.browser.sourceReady.connect(lambda url, text, rendered: self.sources.append((url, text, rendered)))
        self.browser.messageRaised.connect(self.messages.append)

    def tearDown(self):
        self.browser.shutdown()
        self.browser.close()
        QtTest.QTest.qWait(100)

    def load_site(self):
        self.browser.load(BASE + '/')
        wait_until(lambda: len(self.captured) >= self.EXPECTED_REQUESTS, what='the page\'s requests')

    def by_url(self, fragment: str):
        return [request for request in self.captured if fragment in request.url]

    def test_the_hook_does_not_break_the_page(self):
        self.load_site()
        wait_until(lambda: run_js(self.browser.page(), 'document.title') == 'fetched 2', what='the fetch result')

    def test_fetch_and_xhr_are_captured_with_bodies(self):
        self.load_site()

        items = self.by_url('/api/items')[0]
        self.assertEqual(items.kind, 'fetch')
        self.assertEqual(items.method, 'GET')
        self.assertEqual(items.status, 200)
        self.assertEqual(items.url, BASE + '/api/items?page=1')
        headers = {name.lower(): value for name, value in items.request_headers.items()}
        self.assertEqual(headers.get('x-requested-with'), 'fetch')
        self.assertTrue(items.is_json)
        self.assertEqual(items.parsed_json()['items'][1]['name'], 'Gadget')
        self.assertEqual(items.page_url, BASE + '/')

        search = self.by_url('/api/search')[0]
        self.assertEqual(search.kind, 'xhr')
        self.assertEqual(search.method, 'POST')
        self.assertEqual(search.request_headers.get('Content-Type'), 'application/json')
        self.assertEqual(json.loads(search.request_body), {'q': 'bolt', 'n': 3})
        self.assertEqual(search.parsed_json()['echo'], {'q': 'bolt', 'n': 3})

        fragment = self.by_url('/fragment')[0]
        self.assertTrue(fragment.is_html)
        self.assertIn('beta', fragment.response_body)

    def test_form_bodies_are_recognised(self):
        self.load_site()
        forms = {request.request_body_kind: request for request in self.by_url('/api/form')}
        self.assertEqual(set(forms), {'multipart', 'urlencoded'})
        self.assertEqual(forms['urlencoded'].request_body, 'c=3&d=four+words')
        self.assertEqual(forms['multipart'].request_body, 'a=1&b=two%20words')

    def test_binary_responses_are_listed_without_a_body(self):
        self.load_site()
        image = self.by_url('/image.png')[0]
        self.assertIsNone(image.response_body)
        self.assertEqual(image.content_type, 'image/png')

    def test_requests_are_numbered_in_order(self):
        self.load_site()
        self.assertEqual([request.number for request in self.captured], list(range(1, len(self.captured) + 1)))

    def test_source_as_served_and_rendered(self):
        self.load_site()
        wait_until(lambda: self.sources, what='the page source')

        url, served, rendered = self.sources[-1]
        self.assertFalse(rendered)
        self.assertEqual(url, BASE + '/')
        self.assertIn('served by the server', served)
        self.assertNotIn('rendered by script', served)

        before = len(self.captured)
        self.browser._rendered.setChecked(True)
        self.browser.request_source()
        wait_until(lambda: self.sources[-1][2], what='the rendered source')
        self.assertIn('rendered by script', self.sources[-1][1])

        self.browser._as_served.setChecked(True)
        self.sources.clear()
        self.browser.request_source()
        wait_until(lambda: self.sources, what='the page source again')
        QtTest.QTest.qWait(200)
        self.assertEqual(len(self.captured), before, 'fetching the source must not show up in the Network list')

    def test_the_engine_token_is_removed_from_the_user_agent(self):
        self.assertNotIn('QtWebEngine', self.browser.user_agent())
        self.assertIn('Chrome/', self.browser.user_agent())

    def test_a_new_window_opens_in_the_same_view(self):
        self.browser.load(BASE + '/')
        wait_until(lambda: len(self.captured) >= self.EXPECTED_REQUESTS, what='the page')
        run_js(self.browser.page(), "document.getElementById('popup').click(); 1")
        wait_until(lambda: self.browser.current_url() == BASE + '/page2', what='the second page')

    def test_bad_addresses_are_reported(self):
        self.browser.load('two words')
        self.assertTrue(self.messages)

    def test_picking_an_element_gives_a_selector(self):
        self.load_site()
        rect = json.loads(run_js(self.browser.page(), """
            (function () {
              var items = document.querySelectorAll('.item .price');
              var r = items[1].getBoundingClientRect();
              return JSON.stringify({x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)});
            })()"""))

        picked = []
        self.browser.elementPicked.connect(lambda pick, what, similar: picked.append((pick, what, similar)))
        self.browser._pick(QtCore.QPoint(rect['x'], rect['y']), 'text', False)
        wait_until(lambda: picked, what='the picked element')

        pick, what, similar = picked[0]
        self.assertEqual(pick['tag'], 'span')
        self.assertEqual(pick['text'], '$19.99')
        self.assertEqual(pick['selector'], 'div.item:nth-of-type(2) > span.price')
        self.assertEqual(pick['similar'], 'span.price')

    def test_picking_nothing_is_reported(self):
        self.load_site()
        self.browser._pick(QtCore.QPoint(-50, -50), 'text', False)
        wait_until(lambda: self.messages, what='the message')


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.panel = browser_dock.ScraperBrowserPanel(None)
        self.panel.resize(1400, 800)
        self.panel.show()

    def tearDown(self):
        self.panel.shutdown()
        self.panel.close()
        QtTest.QTest.qWait(100)

    def run_script(self, document: str = '', json_value: object = None) -> dict:
        namespace = {}
        with no_network(document, json_value):
            exec(compile(self.panel.inspector.pane.text(), '<script>', 'exec'), namespace)
        return namespace

    def load_site(self):
        self.panel.browser.load(BASE + '/')
        wait_until(lambda: self.panel.inspector.network.request_count() >= 6, what='the page\'s requests')
        wait_until(lambda: self.panel.inspector.source.document_text(), what='the source')
        wait_until(lambda: not self.panel.inspector.source._jobs, what='the source to finish loading')

    def test_json_from_a_captured_request_to_a_script(self):
        self.load_site()
        inspector = self.panel.inspector

        rows = [inspector.network._filter.index(row, 6).data() for row in range(inspector.network.visible_request_count())]
        row = [index for index, url in enumerate(rows) if url.startswith('/api/items')][0]
        inspector.network.select_row(row)

        tree = inspector.response._tree
        root = tree.topLevelItem(0)
        root.setExpanded(True)
        items = [root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == 'items'][0]
        items.setExpanded(True)
        first = items.child(0)
        first.setExpanded(True)
        tree.clearSelection()
        for index in range(first.childCount()):
            if first.child(index).text(0) == 'price':
                first.child(index).setSelected(True)
        inspector.response._every_item.setChecked(True)
        inspector.response._extract.click()

        script = inspector.pane.text()
        self.assertIn('X-Requested-With', script)
        self.assertIn('Referer', script)
        namespace = self.run_script(json_value={'items': [{'price': 1}, {'price': 2}]})
        self.assertEqual(namespace['price_values'], [1, 2])

    def test_source_selection_to_a_script(self):
        self.load_site()
        inspector = self.panel.inspector
        document = inspector.source.document_text()

        start = document.index('$19.99')
        inspector.source.select_range(start, start + len('$19.99'))
        menu = inspector.source.build_menu()
        css = [child for child in menu.findChildren(QtWidgets.QMenu) if 'CSS selector' in child.title()][0]
        action = [a for a in css.actions() if 'Text of this' in a.text()][0]
        action.trigger()

        namespace = self.run_script(document)
        self.assertEqual(namespace['value'], '$19.99')
        self.assertIn(BASE + '/', inspector.pane.text())

    def test_show_selected_text_in_source(self):
        self.load_site()
        self.panel.browser.showInSourceRequested.emit('served by the server')
        selection = self.panel.inspector.source.selection()
        document = self.panel.inspector.source.document_text()
        self.assertEqual(document[selection[0]:selection[1]], 'served by the server')
        self.assertIs(self.panel.inspector.tabs.currentWidget(), self.panel.inspector.source)

    def test_a_pick_in_the_live_page_becomes_code_and_downloads_the_page_first(self):
        self.load_site()
        inspector = self.panel.inspector
        pick = browser_pick.parse_pick(json.dumps({
            'tag': 'span', 'selector': 'div.item:nth-of-type(2) > span.price', 'similar': 'span.price',
            'text': '$19.99', 'href': '', 'src': ''}))
        self.panel.browser.elementPicked.emit(pick, 'text', False)

        script = inspector.pane.text()
        self.assertLess(script.index('requests.get'), script.index('select_one'))
        document = (PAGE).decode()
        namespace = self.run_script(document)
        self.assertEqual(namespace['value'], '$19.99')

    def test_clearing_the_network_list(self):
        self.load_site()
        self.panel.inspector.network.clear()
        self.assertEqual(self.panel.inspector.network.request_count(), 0)


class DockTests(unittest.TestCase):
    def test_the_dock_is_created_without_touching_the_real_app_data(self):
        import tempfile

        paths = _bootstrap.load('utils.paths')
        original = paths.get_appdata
        with tempfile.TemporaryDirectory() as folder:
            paths.get_appdata = lambda: folder
            try:
                window = QtWidgets.QMainWindow()
                dock = browser_dock.ScraperBrowser(window)
                window.resize(1400, 800)
                window.show()
                self.assertTrue(dock.IsShown())
                self.assertEqual(dock.dock.objectName(), 'scraper_browser')
                self.assertIsInstance(dock.panel, browser_dock.ScraperBrowserPanel)
                dock.panel.browser.load(BASE + '/page2')
                wait_until(lambda: dock.panel.browser.current_url() == BASE + '/page2', what='the page')
                dock.Destroy()
                QtTest.QTest.qWait(200)
                window.close()
            finally:
                paths.get_appdata = original


if __name__ == '__main__':
    unittest.main()
