# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The browser's pure helpers: address-bar input and picked elements."""

import json
import unittest

from tests import _bootstrap

url_input = _bootstrap.load('scraping.url_input')
browser_pick = _bootstrap.load('scraping.browser_pick')

PICK = {
    'tag': 'span', 'selector': 'div.item:nth-of-type(2) > span.price', 'similar': 'span.price',
    'text': '$19.99', 'href': '/buy/2', 'src': ''}

PAGE = ('<div class="item"><span class="price">$9.99</span></div>'
        '<div class="item"><span class="price">$19.99</span></div>')


class NormalizeUrl(unittest.TestCase):
    def test_bare_hosts_get_https(self):
        self.assertEqual(url_input.normalize_url('example.com'), 'https://example.com')
        self.assertEqual(url_input.normalize_url('  example.com/shop?x=1 '), 'https://example.com/shop?x=1')

    def test_local_addresses_get_http(self):
        self.assertEqual(url_input.normalize_url('localhost:8000/x'), 'http://localhost:8000/x')
        self.assertEqual(url_input.normalize_url('127.0.0.1:5000'), 'http://127.0.0.1:5000')
        self.assertEqual(url_input.normalize_url('192.168.1.10'), 'http://192.168.1.10')
        self.assertEqual(url_input.normalize_url('[::1]:8080'), 'http://[::1]:8080')

    def test_schemes_are_left_alone(self):
        for text in ('http://example.com', 'https://example.com/a', 'file:///c:/page.html', 'about:blank',
                     'view-source:https://example.com', 'ftp://example.com/x'):
            with self.subTest(text=text):
                self.assertEqual(url_input.normalize_url(text), text)

    def test_nonsense_is_rejected(self):
        for text in ('', '   ', 'two words', 'a b.com'):
            with self.subTest(text=text):
                self.assertEqual(url_input.normalize_url(text), '')


class ParsePick(unittest.TestCase):
    def test_a_well_formed_answer(self):
        pick = browser_pick.parse_pick(json.dumps(PICK))
        self.assertEqual(pick, PICK)

    def test_missing_fields_become_empty_strings(self):
        pick = browser_pick.parse_pick(json.dumps({'tag': 'p', 'selector': 'p'}))
        self.assertEqual(pick['href'], '')
        self.assertEqual(pick['text'], '')

    def test_garbage_is_rejected(self):
        for answer in (None, 5, 'nope', '[]', '"x"', json.dumps({'tag': 5, 'selector': 'a'}),
                       json.dumps({'tag': 'a', 'selector': 'x' * 5000})):
            with self.subTest(answer=answer):
                self.assertIsNone(browser_pick.parse_pick(answer))

    def test_long_text_is_cut(self):
        pick = browser_pick.parse_pick(json.dumps(dict(PICK, text='x' * 5000)))
        self.assertEqual(len(pick['text']), 500)

    def test_script_has_the_position_filled_in(self):
        script = browser_pick.pick_script(12, 34)
        self.assertIn('(12, 34)', script)
        self.assertNotIn('%X%', script)
        self.assertNotIn('%Y%', script)


class PickSnippet(unittest.TestCase):
    def run_code(self, snippet, document=PAGE):
        namespace = {'html': document}
        for line in snippet.imports:
            exec(line, namespace)
        exec(snippet.code, namespace)
        return namespace

    def test_text_of_one_element(self):
        snippet = browser_pick.pick_snippet(PICK)
        self.assertEqual(self.run_code(snippet)['value'], '$19.99')
        self.assertIn(browser_pick.RENDERED_WARNING, snippet.warnings)

    def test_text_of_every_similar_element(self):
        snippet = browser_pick.pick_snippet(PICK, every_similar=True)
        self.assertEqual(self.run_code(snippet)['values'], ['$9.99', '$19.99'])

    def test_attribute(self):
        document = '<a class="buy" href="/buy/2">Buy</a>'
        pick = dict(PICK, tag='a', selector='a.buy', similar='a.buy')
        snippet = browser_pick.pick_snippet(pick, 'href')
        self.assertEqual(self.run_code(snippet, document)['href'], '/buy/2')

    def test_attribute_of_every_similar_element(self):
        document = '<a class="buy" href="/a">1</a><a class="buy" href="/b">2</a>'
        pick = dict(PICK, tag='a', selector='a.buy', similar='a.buy')
        snippet = browser_pick.pick_snippet(pick, 'href', every_similar=True)
        self.assertEqual(self.run_code(snippet, document)['values'], ['/a', '/b'])

    def test_missing_attribute_is_an_error(self):
        with self.assertRaises(ValueError):
            browser_pick.pick_snippet(dict(PICK, src=''), 'src')

    def test_unknown_attribute_is_an_error(self):
        with self.assertRaises(ValueError):
            browser_pick.pick_snippet(PICK, 'onclick')

    def test_no_selector_is_an_error(self):
        with self.assertRaises(ValueError):
            browser_pick.pick_snippet(dict(PICK, selector=''))

    def test_a_hostile_selector_cannot_break_out_of_the_string(self):
        selector = "x'); import os; os.system('echo pwned'); ('"
        snippet = browser_pick.pick_snippet(dict(PICK, selector=selector))
        compile(snippet.code, '<snippet>', 'exec')
        self.assertEqual(snippet.code.count('\n'), 1)
        self.assertNotIn("\nimport os", snippet.code)

    def test_a_selector_with_a_newline_stays_one_statement(self):
        snippet = browser_pick.pick_snippet(dict(PICK, selector='a\nb = 1'))
        tree = compile(snippet.code, '<snippet>', 'exec', flags=0x400)  # PyCF_ONLY_AST
        self.assertEqual(len(tree.body), 2)

    def test_names_avoid_the_script(self):
        snippet = browser_pick.pick_snippet(PICK, taken={'value', 'soup'})
        self.assertIn('value_2 = ', snippet.code)
        self.assertNotIn('BeautifulSoup(', snippet.code)


if __name__ == '__main__':
    unittest.main()
