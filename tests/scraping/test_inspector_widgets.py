# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The inspector widgets, driven headless: select text, trigger the menu
action, and run the script that comes out."""

import contextlib
import json
import os
import sys
import types
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6 import QtCore, QtGui, QtTest, QtWidgets  # noqa: E402

from tests import _bootstrap  # noqa: E402
from tests.scraping import sample_pages  # noqa: E402

snippets = _bootstrap.load('scraping.snippets')
request_code = _bootstrap.load('scraping.request_code')
capture_model = _bootstrap.load('scraping.capture_model')
source_viewer = _bootstrap.load('ui.scraper_inspector.source_viewer')
json_tree = _bootstrap.load('ui.scraper_inspector.json_tree')
network_panel = _bootstrap.load('ui.scraper_inspector.network_panel')
inspector_module = _bootstrap.load('ui.scraper_inspector.inspector')
insertion = _bootstrap.load('ui.scraper_inspector.insertion')
snippet_pane = _bootstrap.load('ui.scraper_inspector.snippet_pane')


APP = _bootstrap.make_app()


def wait_until(predicate, timeout: float = 8.0) -> None:
    waited = 0.0
    while not predicate():
        QtTest.QTest.qWait(20)
        waited += 0.02
        if waited > timeout:
            raise AssertionError('timed out waiting for the widget')


# Never call QAction.menu() in a test: the wrapper it returns OWNS the
# submenu, so when a temporary one is collected the submenu and every action
# in it are destroyed (the widgets themselves never call it). Submenus are
# found through findChildren, which returns non-owning wrappers.
def find_submenu(menu: QtWidgets.QMenu, title: str):
    for child in menu.findChildren(QtWidgets.QMenu, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
        if title in child.title():
            return child

    return None


def find_action(menu: QtWidgets.QMenu, text: str):
    """The (non-submenu) action whose text contains *text*, searching submenus."""
    submenu_actions = {child.menuAction() for child in menu.findChildren(
        QtWidgets.QMenu, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly)}

    for action in menu.actions():
        if action in submenu_actions:
            continue

        if text in action.text():
            return action

    for child in menu.findChildren(QtWidgets.QMenu, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
        found = find_action(child, text)
        if found is not None:
            return found

    return None


def fake_requests(document: str = '', json_value: object = None):
    calls = []

    def make(verb):
        def call(*args, **kwargs):
            calls.append((verb, args, kwargs))
            return types.SimpleNamespace(
                raise_for_status=lambda: None, text=document, json=lambda: json_value)
        return call

    return types.SimpleNamespace(get=make('get'), post=make('post'), request=make('request')), calls


@contextlib.contextmanager
def no_network(document: str = '', json_value: object = None):
    """Make ``import requests`` give a fake for the duration, so a script
    under test can never reach the network."""
    module, calls = fake_requests(document, json_value)
    original = sys.modules.get('requests')
    sys.modules['requests'] = module
    try:
        yield calls
    finally:
        if original is None:
            del sys.modules['requests']
        else:
            sys.modules['requests'] = original


def make_request(number: int = 1, **overrides) -> capture_model.CapturedRequest:
    values = {
        'kind': 'fetch', 'method': 'GET', 'url': 'https://example.com/api/items?page=1', 'status': 200,
        'requestHeaders': {'Accept': 'application/json'}, 'requestBody': None, 'requestBodyKind': '',
        'responseHeaders': {'content-type': 'application/json'},
        'responseBody': json.dumps({'total': 2, 'items': [
            {'name': 'Widget', 'price': 9.99}, {'name': 'Gadget', 'price': 19.99}]}),
        'responseTruncated': False, 'pageUrl': 'https://example.com/shop', 'userAgent': 'UA/1', 'durationMs': 5}
    values.update(overrides)
    return capture_model.parse_record(json.dumps(values), number)


class SourceViewerTests(unittest.TestCase):
    def setUp(self):
        self.viewer = source_viewer.SourceViewer()
        self.viewer.resize(700, 400)
        self.viewer.show()
        self.collected = []
        self.viewer.snippetReady.connect(self.collected.append)
        self.viewer.set_taken_provider(
            lambda: snippets.taken_names('\n'.join(snippet.code for snippet in self.collected)))
        self.viewer.set_preamble(
            lambda taken: request_code.generate_page_load('https://example.com/shop', taken=taken))

    def tearDown(self):
        self.viewer.close()

    def load(self, document: str) -> None:
        self.viewer.set_document(document, 'html', 'html')
        wait_until(lambda: not self.viewer._jobs)

    def run_collected(self, document: str) -> dict:
        namespace = {}
        with no_network(document):
            for snippet in self.collected:
                for line in snippet.imports:
                    exec(line, namespace)
                exec(snippet.code, namespace)
        return namespace

    def test_displayed_text_is_what_qt_keeps(self):
        for name, document in sample_pages.ALL_PAGES.items():
            with self.subTest(page=name):
                self.load(document)
                self.assertEqual(self.viewer.displayed_text(), self.viewer._wrap.display)

    def test_selection_maps_back_to_the_original_offsets(self):
        for name, document in sample_pages.ALL_PAGES.items():
            self.load(document)
            for start, end in sample_pages.text_nodes(document):
                with self.subTest(page=name, selected=document[start:end]):
                    self.viewer.select_range(start, end)
                    self.assertEqual(self.viewer.selection(), (start, end))

    def test_a_minified_page_is_shown_on_short_lines(self):
        self.load(sample_pages.MINIFIED * 40)
        self.assertTrue(all(len(line) <= 160 for line in self.viewer.displayed_text().split('\n')))

    def test_menu_without_a_selection(self):
        self.load(sample_pages.LISTING)
        menu = self.viewer.build_menu()
        self.assertIsNotNone(find_action(menu, 'Select some text'))
        self.assertIsNone(find_action(menu, 'Take the text after'))

    def test_text_after_through_the_menu_loads_the_page_first(self):
        for name, document in sample_pages.ALL_PAGES.items():
            self.collected.clear()
            self.load(document)
            start, end = sample_pages.text_nodes(document)[2]
            self.viewer.select_range(start, end)

            with self.subTest(page=name):
                find_action(self.viewer.build_menu(), 'Take the text after this').trigger()
                self.assertEqual(len(self.collected), 2)
                self.assertIn('requests.get', self.collected[0].code)
                self.assertEqual(self.run_collected(document)['after'], document[end:])

    def test_preamble_is_not_repeated(self):
        self.load(sample_pages.LISTING)
        start, end = sample_pages.text_nodes(sample_pages.LISTING)[3]
        self.viewer.select_range(start, end)
        find_action(self.viewer.build_menu(), 'Take the text after this').trigger()
        find_action(self.viewer.build_menu(), 'Take the text before this').trigger()
        self.assertEqual(len(self.collected), 3)

    def test_every_string_and_regex_action_reproduces_the_selection(self):
        document = sample_pages.LISTING
        self.load(document)
        start = document.index('Gadget')
        end = start + len('Gadget')
        self.viewer.select_range(start, end)

        expectations = {
            'Take the text before this': ('before', document[:start]),
            'Index of the start': ('position', start),
            'Index just past': ('end', end),
            'Capture this one': ('value', 'Gadget'),
        }
        for title, (variable, expected) in expectations.items():
            with self.subTest(action=title):
                self.collected.clear()
                find_action(self.viewer.build_menu(), title).trigger()
                self.assertEqual(self.run_collected(document)[variable], expected)

    def test_css_and_xpath_actions(self):
        document = sample_pages.LISTING
        self.load(document)
        start = document.index('$19.99')
        end = start + len('$19.99')
        self.viewer.select_range(start, end)

        for title in ('Text of this <span>',):
            with self.subTest(action=title):
                self.collected.clear()
                menu = self.viewer.build_menu()
                css = find_submenu(menu, 'CSS selector')
                find_action(css, title).trigger()
                self.assertEqual(self.run_collected(document)['value'], '$19.99')

                self.collected.clear()
                xpath = find_submenu(menu, 'XPath')
                find_action(xpath, title).trigger()
                self.assertEqual(self.run_collected(document)['value'], '$19.99')

    def test_attribute_actions_only_appear_inside_an_attribute(self):
        document = sample_pages.LISTING
        self.load(document)

        start = document.index('$19.99')
        self.viewer.select_range(start, start + 6)
        self.assertIsNone(find_action(self.viewer.build_menu(), 'attribute'))

        start = document.index('/p/2')
        self.viewer.select_range(start, start + 4)
        self.collected.clear()
        menu = self.viewer.build_menu()
        css = find_submenu(menu, 'CSS selector')
        find_action(css, 'The "href" attribute').trigger()
        self.assertEqual(self.run_collected(document)['href'], '/p/2')

    def test_between_mark_flow(self):
        document = sample_pages.LISTING
        self.load(document)
        first = document.index('Gadget')
        self.viewer.select_range(first, first + len('Gadget'))
        find_action(self.viewer.build_menu(), 'Mark as the start').trigger()

        second = document.index('Doohickey')
        self.viewer.select_range(second, second + len('Doohickey'))
        self.collected.clear()
        find_action(self.viewer.build_menu(), 'between the marked start').trigger()
        self.assertEqual(self.run_collected(document)['value'], document[first + len('Gadget'):second])

    def test_between_is_not_offered_when_the_selection_is_before_the_mark(self):
        document = sample_pages.LISTING
        self.load(document)
        later = document.index('Doohickey')
        self.viewer.select_range(later, later + len('Doohickey'))
        find_action(self.viewer.build_menu(), 'Mark as the start').trigger()

        earlier = document.index('Gadget')
        self.viewer.select_range(earlier, earlier + len('Gadget'))
        self.assertIsNone(find_action(self.viewer.build_menu(), 'between the marked start'))

    def test_unlocatable_selection_reports_instead_of_raising(self):
        document = '<p>x</p> trailing text outside any element'
        self.load(document)
        messages = []
        self.viewer.messageRaised.connect(messages.append)
        start = document.index('trailing')
        self.viewer.select_range(start, start + len('trailing'))
        menu = self.viewer.build_menu()
        self.assertFalse(find_submenu(menu, 'CSS selector').isEnabled())
        self.assertEqual(messages, [])

    def test_select_text_finds_rendered_text(self):
        document = sample_pages.LISTING
        self.load(document)
        self.assertTrue(self.viewer.select_text('Prices & availability change daily.'))
        start, end = self.viewer.selection()
        self.assertEqual(document[start:end], 'Prices &amp; availability change daily.')
        self.assertTrue(self.viewer.select_text('In   stock'))
        self.assertFalse(self.viewer.select_text('not on the page'))

    def test_highlighting_is_applied(self):
        self.load(sample_pages.LISTING)
        block = self.viewer._edit.document().findBlockByNumber(11)
        formats = block.layout().formats()
        self.assertTrue(formats, 'expected highlighted ranges on a line of markup')


class JsonTreeTests(unittest.TestCase):
    sample = {
        'total': 2,
        'items': [
            {'name': 'Widget', 'price': 9.99, 'tags': ['a', 'b']},
            {'name': 'Gadget', 'price': 19.99, 'tags': ['c']},
        ],
    }

    def setUp(self):
        self.tree = json_tree.JsonTree()
        self.tree.resize(500, 400)
        self.collected = []
        self.messages = []
        self.tree.snippetReady.connect(self.collected.append)
        self.tree.messageRaised.connect(self.messages.append)
        self.tree.set_value(self.sample)

    def item_at(self, path):
        item = self.tree.topLevelItem(0)
        for step in path:
            item.setExpanded(True)
            for index in range(item.childCount()):
                child = item.child(index)
                if tuple(child.data(0, QtCore.Qt.ItemDataRole.UserRole))[-1:] == (step,):
                    item = child
                    break
            else:
                raise AssertionError(f'no row for {step!r}')

        return item

    def select(self, *paths):
        self.tree.clearSelection()
        for path in paths:
            self.item_at(path).setSelected(True)

    def run_collected(self):
        namespace = {'data': self.sample}
        for snippet in self.collected:
            exec(snippet.code, namespace)
        return namespace

    def test_rows_show_keys_and_values(self):
        root = self.tree.topLevelItem(0)
        self.assertEqual(root.text(0), 'data')
        self.assertEqual(root.text(1), '{2 key(s)}')
        self.assertEqual(self.item_at(('total',)).text(1), '2')
        self.assertEqual(self.item_at(('items', 0, 'name')).text(1), '"Widget"')

    def test_single_value(self):
        self.select(('items', 1, 'name'))
        self.assertTrue(self.tree.extract_selected())
        self.assertEqual(self.run_collected()['name'], 'Gadget')

    def test_several_fields_of_one_element_become_a_loop(self):
        self.select(('items', 0, 'name'), ('items', 0, 'price'))
        self.tree.extract_selected()
        self.assertEqual(self.run_collected()['results'], [
            {'name': 'Widget', 'price': 9.99}, {'name': 'Gadget', 'price': 19.99}])

    def test_every_item(self):
        self.select(('items', 0, 'price'))
        self.assertTrue(self.tree.can_extract_every_item())
        self.tree.extract_selected(every_item=True)
        self.assertEqual(self.run_collected()['price_values'], [9.99, 19.99])

    def test_every_item_is_not_offered_outside_an_array(self):
        self.select(('total',))
        self.assertFalse(self.tree.can_extract_every_item())

    def test_renamed_variable(self):
        self.select(('total',))
        self.item_at(('total',)).setText(2, 'how_many')
        self.tree.extract_selected()
        self.assertEqual(self.run_collected()['how_many'], 2)

    def test_names_avoid_the_script(self):
        self.tree.set_taken_provider(lambda: {'price', 'data'})
        self.select(('items', 0, 'price'))
        self.tree.extract_selected()
        self.assertIn('price_2 = ', self.collected[-1].code)

    def test_nothing_selected_says_so(self):
        self.tree.clearSelection()
        self.assertFalse(self.tree.extract_selected())
        self.assertTrue(self.messages)

    def test_preamble_loads_the_json_when_missing(self):
        spec = request_code.RequestSpec(method='GET', url='https://example.com/api', response_is_json=True)
        self.tree.set_preamble(lambda taken: request_code.generate_request_code(spec, taken=taken))
        self.select(('total',))
        self.tree.extract_selected()
        self.assertEqual(len(self.collected), 2)
        self.assertIn('data = response.json()', self.collected[0].code)

    def test_big_arrays_are_shown_in_part(self):
        self.tree.set_value({'rows': list(range(5000))})
        rows = self.item_at(('rows',))
        rows.setExpanded(True)
        self.assertEqual(rows.childCount(), json_tree._MAX_CHILDREN + 1)
        self.assertIn('more not shown', rows.child(rows.childCount() - 1).text(1))

    def test_selection_in_document_order(self):
        self.select(('items', 1, 'name'), ('total',), ('items', 0, 'name'))
        self.assertEqual(self.tree.selected_paths(), [('total',), ('items', 0, 'name'), ('items', 1, 'name')])


class NetworkPanelTests(unittest.TestCase):
    def setUp(self):
        self.panel = network_panel.NetworkPanel()
        self.selected = []
        self.panel.requestSelected.connect(self.selected.append)

    def test_rows_and_selection(self):
        self.panel.add_request(make_request(1))
        self.panel.add_request(make_request(2, url='https://example.com/page.html',
                                            responseHeaders={'content-type': 'text/html'},
                                            responseBody='<p>x</p>'))
        self.assertEqual(self.panel.request_count(), 2)
        self.panel.select_row(1)
        self.assertEqual(self.selected[-1].number, 2)

    def test_filters(self):
        self.panel.add_request(make_request(1))
        self.panel.add_request(make_request(2, url='https://example.com/page.html',
                                            responseHeaders={'content-type': 'text/html'},
                                            responseBody='<p>x</p>'))
        self.panel._search.setText('page.html')
        self.assertEqual(self.panel.visible_request_count(), 1)
        self.panel._search.setText('')
        self.panel._json_only.setChecked(True)
        self.assertEqual(self.panel.visible_request_count(), 1)

    def test_clear(self):
        cleared = []
        self.panel.requestsCleared.connect(lambda: cleared.append(True))
        self.panel.add_request(make_request(1))
        self.panel.clear()
        self.assertEqual(self.panel.request_count(), 0)
        self.assertEqual(cleared, [True])

    def test_the_list_is_a_rolling_window(self):
        original = network_panel.MAX_REQUESTS
        network_panel.MAX_REQUESTS = 3
        try:
            for number in range(1, 6):
                self.panel.add_request(make_request(number))
        finally:
            network_panel.MAX_REQUESTS = original

        self.assertEqual(self.panel.request_count(), 3)
        self.panel.select_row(0)
        self.assertEqual(self.selected[-1].number, 3)


class InspectorTests(unittest.TestCase):
    def setUp(self):
        self.inspector = inspector_module.ScraperInspector()
        self.inspector.resize(900, 700)
        self.inspector.show()

    def tearDown(self):
        self.inspector.close()

    def script(self) -> str:
        return self.inspector.pane.text()

    def run_script(self, document: str = '', json_value: object = None) -> dict:
        namespace = {}
        with no_network(document, json_value):
            exec(compile(self.script(), '<script>', 'exec'), namespace)
        return namespace

    def test_json_flow_from_request_to_extracted_values(self):
        sample = {'total': 2, 'items': [{'name': 'Widget', 'price': 9.99}, {'name': 'Gadget', 'price': 19.99}]}
        self.inspector.add_request(make_request(1))
        self.inspector.network.select_row(0)
        self.assertIs(self.inspector.tabs.currentWidget(), self.inspector.response)

        tree = self.inspector.response._tree
        items = tree.topLevelItem(0)
        items.setExpanded(True)
        items_row = [items.child(i) for i in range(items.childCount()) if items.child(i).text(0) == 'items'][0]
        items_row.setExpanded(True)
        first = items_row.child(0)
        first.setExpanded(True)
        tree.clearSelection()
        for index in range(first.childCount()):
            if first.child(index).text(0) in ('name', 'price'):
                first.child(index).setSelected(True)

        self.inspector.response._extract.click()

        script = self.script()
        self.assertTrue(script.startswith('import requests'), script)
        namespace = self.run_script(json_value=sample)
        self.assertEqual(namespace['results'], [
            {'name': 'Widget', 'price': 9.99}, {'name': 'Gadget', 'price': 19.99}])

    def test_html_flow_from_page_source_to_values(self):
        document = sample_pages.LISTING
        self.inspector.set_page_source('https://example.com/shop?page=1', document, False, 'UA/1')
        wait_until(lambda: not self.inspector.source._jobs)

        start = document.index('$19.99')
        self.inspector.source.select_range(start, start + len('$19.99'))
        menu = self.inspector.source.build_menu()
        css = find_submenu(menu, 'CSS selector')
        find_action(css, 'Text of this <span>').trigger()

        script = self.script()
        self.assertIn('import requests', script)
        self.assertIn('from bs4 import BeautifulSoup', script)
        self.assertLess(script.index('import requests'), script.index('html = '))
        namespace = self.run_script(document)
        self.assertEqual(namespace['value'], '$19.99')

    def test_rendered_source_warns(self):
        document = sample_pages.LISTING
        self.inspector.set_page_source('https://example.com/shop', document, True)
        wait_until(lambda: not self.inspector.source._jobs)

        start = document.index('Gadget')
        self.inspector.source.select_range(start, start + len('Gadget'))
        find_action(self.inspector.source.build_menu(), 'Take the text after this').trigger()
        self.assertIn('rendered page', self.script())

    def test_response_html_fragment_flow(self):
        fragment = '<ul><li class="hit">alpha</li><li class="hit">beta</li></ul>'
        request = make_request(1, url='https://example.com/search?q=x',
                               responseHeaders={'content-type': 'text/html'}, responseBody=fragment)
        self.inspector.add_request(request)
        self.inspector.network.select_row(0)
        source = self.inspector.response._source
        wait_until(lambda: not source._jobs)

        start = fragment.index('beta')
        source.select_range(start, start + 4)
        menu = source.build_menu()
        css = find_submenu(menu, 'CSS selector')
        find_action(css, 'every similar').trigger()

        namespace = self.run_script(fragment)
        self.assertEqual(namespace['values'], ['alpha', 'beta'])

    def test_repeat_request_button(self):
        self.inspector.add_request(make_request(1))
        self.inspector.network.select_row(0)
        self.inspector.response._replay.click()
        namespace = self.run_script(json_value={'ok': True})
        self.assertEqual(namespace['data'], {'ok': True})

    def test_clearing_the_network_list_clears_the_response(self):
        self.inspector.add_request(make_request(1))
        self.inspector.network.select_row(0)
        self.inspector.network.clear()
        self.assertIsNone(self.inspector.response.current_request())

    def test_external_sink_replaces_the_pane(self):
        class Sink(insertion.SnippetSink):
            def __init__(self):
                self.snippets = []

            def taken_names(self):
                return set()

            def insert_snippet(self, snippet):
                self.snippets.append(snippet)

        sink = Sink()
        self.inspector.set_sink(sink)
        self.assertFalse(self.inspector.pane.isVisible())

        document = sample_pages.LISTING
        self.inspector.set_page_source('https://example.com/shop', document, False)
        wait_until(lambda: not self.inspector.source._jobs)
        start = document.index('Gadget')
        self.inspector.source.select_range(start, start + len('Gadget'))
        find_action(self.inspector.source.build_menu(), 'Take the text after this').trigger()
        self.assertEqual(len(sink.snippets), 2)
        self.assertEqual(self.inspector.pane.text(), '')

        self.inspector.set_sink(None)
        self.assertTrue(self.inspector.pane.isVisible())


class InsertionTests(unittest.TestCase):
    def setUp(self):
        self.pane = snippet_pane.SnippetPane()

    def snippet(self, code: str, imports=(), warnings=()):
        return snippets.Snippet(code=code, description='test', imports=list(imports), warnings=list(warnings))

    def test_imports_are_merged_once_and_code_follows(self):
        self.pane.insert_snippet(self.snippet('a = re.compile("x")', ['import re']))
        self.pane.insert_snippet(self.snippet('b = re.compile("y")', ['import re', 'import os']))
        text = self.pane.text()
        self.assertEqual(text.count('import re'), 1)
        self.assertTrue(text.startswith('import re\nimport os\n'), text)
        compile(text, '<script>', 'exec')

    def test_warnings_become_comments(self):
        self.pane.insert_snippet(self.snippet('x = 1', warnings=['Check this.']))
        self.assertIn('# NOTE: Check this.\nx = 1', self.pane.text())

    def test_each_insertion_is_one_undo_step(self):
        self.pane.insert_snippet(self.snippet('a = 1'))
        after_first = self.pane.text()
        self.pane.insert_snippet(self.snippet('b = re.compile("y")', ['import re']))
        self.pane._editor.undo()
        self.assertEqual(self.pane.text(), after_first)

    def test_new_code_goes_below_the_cursor_line(self):
        self.pane.insert_snippet(self.snippet('first = 1'))
        self.pane.insert_snippet(self.snippet('third = 3'))
        editor = self.pane._editor
        cursor = editor.textCursor()
        cursor.setPosition(0)
        editor.setTextCursor(cursor)
        self.pane.insert_snippet(self.snippet('second = 2'))
        lines = [line for line in self.pane.text().split('\n') if line]
        self.assertEqual(lines, ['first = 1', 'second = 2', 'third = 3'])

    def test_names_come_from_the_script(self):
        self.pane.insert_snippet(self.snippet('html = get()'))
        self.assertIn('html', self.pane.taken_names())

    def test_script_ending_right_after_its_imports(self):
        self.pane._editor.setPlainText('import os')
        self.pane.insert_snippet(self.snippet('x = re.compile("y")', ['import re']))
        compile(self.pane.text(), '<script>', 'exec')
        self.assertIn('import re', self.pane.text().split('\n')[1])


if __name__ == '__main__':
    unittest.main()
