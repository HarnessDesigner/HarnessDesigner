# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The captured-request model, the hook script text, the soft-wrap position
map, and the helpers that put snippets into a script."""

import json
import random
import types
import unittest

from tests import _bootstrap
from tests.scraping import sample_pages

capture_model = _bootstrap.load('scraping.capture_model')
capture_hook = _bootstrap.load('scraping.capture_hook')
request_code = _bootstrap.load('scraping.request_code')
soft_wrap = _bootstrap.load('scraping.soft_wrap')
script_builder = _bootstrap.load('scraping.script_builder')
json_extract = _bootstrap.load('scraping.json_extract')
snippets = _bootstrap.load('scraping.snippets')


def record(**overrides) -> str:
    base = {
        'kind': 'fetch', 'method': 'get', 'url': 'https://example.com/api/items?page=2', 'status': 200,
        'requestHeaders': {'Accept': 'application/json'}, 'requestBody': None, 'requestBodyKind': '',
        'responseHeaders': {'Content-Type': 'application/json; charset=utf-8', 'Content-Length': '42'},
        'responseBody': '{"items": [{"name": "Widget", "price": 9.99}]}', 'responseTruncated': False,
        'pageUrl': 'https://example.com/shop', 'userAgent': 'Mozilla/5.0 Test', 'durationMs': 12}
    base.update(overrides)
    return json.dumps(base)


class ParseRecord(unittest.TestCase):
    def test_well_formed_record(self):
        captured = capture_model.parse_record(record(), 7)
        self.assertEqual(captured.number, 7)
        self.assertEqual(captured.method, 'GET')
        self.assertEqual(captured.status, 200)
        self.assertEqual(captured.content_type, 'application/json')
        self.assertEqual(captured.display_url, '/api/items?page=2')
        self.assertEqual(captured.size, 42)
        self.assertEqual(captured.response_headers['content-type'], 'application/json; charset=utf-8')

    def test_garbage_is_rejected(self):
        for text in ('not json', '[]', '"x"', '{}', json.dumps({'url': 5, 'method': 'GET'}),
                     json.dumps({'url': 'https://x.test/', 'method': None})):
            with self.subTest(text=text):
                self.assertIsNone(capture_model.parse_record(text, 1))

    def test_oversized_record_is_rejected(self):
        text = record(responseBody='x' * (capture_model.MAX_RECORD_CHARS + 1))
        self.assertIsNone(capture_model.parse_record(text, 1))

    def test_wrong_types_are_coerced_not_trusted(self):
        captured = capture_model.parse_record(
            record(status='200', durationMs=None, kind='websocket', requestHeaders=['x'], error=5), 1)
        self.assertEqual(captured.status, 0)
        self.assertEqual(captured.duration_ms, 0)
        self.assertEqual(captured.kind, 'xhr')
        self.assertEqual(captured.request_headers, {})
        self.assertIsNone(captured.error)

    def test_size_falls_back_to_the_body_length(self):
        captured = capture_model.parse_record(record(responseHeaders={}, responseBody='héllo'), 1)
        self.assertEqual(captured.size, len('héllo'.encode('utf-8')))

    def test_describe_size(self):
        self.assertEqual(capture_model.describe_size(10), '10 B')
        self.assertEqual(capture_model.describe_size(2048), '2.0 KB')
        self.assertEqual(capture_model.describe_size(3 * 1024 * 1024), '3.0 MB')


class Classification(unittest.TestCase):
    def test_json_by_content_type(self):
        self.assertTrue(capture_model.parse_record(record(), 1).is_json)

    def test_json_sniffed_from_a_mislabelled_body(self):
        captured = capture_model.parse_record(
            record(responseHeaders={'content-type': 'text/plain'}, responseBody='  {"a": 1}'), 1)
        self.assertTrue(captured.is_json)
        self.assertEqual(captured.parsed_json(), {'a': 1})

    def test_plain_text_is_not_json(self):
        captured = capture_model.parse_record(
            record(responseHeaders={'content-type': 'text/plain'}, responseBody='hello'), 1)
        self.assertFalse(captured.is_json)

    def test_invalid_json_is_not_json(self):
        captured = capture_model.parse_record(record(responseBody='{"a": '), 1)
        self.assertFalse(captured.is_json)

    def test_truncated_body_is_not_parsed(self):
        captured = capture_model.parse_record(record(responseTruncated=True), 1)
        self.assertFalse(captured.is_json)

    def test_json_null_is_still_json(self):
        captured = capture_model.parse_record(record(responseBody='null'), 1)
        self.assertTrue(captured.is_json)

    def test_html_by_type_and_by_sniffing(self):
        by_type = capture_model.parse_record(
            record(responseHeaders={'content-type': 'text/html'}, responseBody='<p>x</p>'), 1)
        by_body = capture_model.parse_record(
            record(responseHeaders={}, responseBody='<!DOCTYPE html><html></html>'), 1)
        self.assertTrue(by_type.is_html)
        self.assertTrue(by_body.is_html)

    def test_xml(self):
        captured = capture_model.parse_record(
            record(responseHeaders={'content-type': 'application/xml'}, responseBody='<a/>'), 1)
        self.assertTrue(captured.is_xml)
        self.assertFalse(captured.is_html)


class ToSpec(unittest.TestCase):
    def test_browser_supplied_headers_are_added(self):
        spec = capture_model.parse_record(record(method='POST'), 1).to_spec()
        self.assertEqual(spec.headers['Referer'], 'https://example.com/shop')
        self.assertEqual(spec.headers['Origin'], 'https://example.com')
        self.assertEqual(spec.headers['User-Agent'], 'Mozilla/5.0 Test')
        self.assertTrue(spec.response_is_json)

    def test_get_has_no_origin(self):
        spec = capture_model.parse_record(record(), 1).to_spec()
        self.assertNotIn('Origin', spec.headers)

    def test_page_set_headers_are_not_overridden(self):
        captured = capture_model.parse_record(record(requestHeaders={'referer': 'https://other.test/'}), 1)
        spec = captured.to_spec()
        self.assertEqual(spec.headers['referer'], 'https://other.test/')
        self.assertNotIn('Referer', spec.headers)

    def test_round_trip_into_requests_code(self):
        captured = capture_model.parse_record(
            record(method='POST', requestHeaders={'Content-Type': 'application/json'},
                   requestBody='{"q": "bolt"}'), 1)
        snippet = request_code.generate_request_code(captured.to_spec())

        calls = []

        def post(*args, **kwargs):
            calls.append((args, kwargs))
            return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {})

        exec(snippet.code, {'requests': types.SimpleNamespace(post=post)})
        self.assertEqual(calls[0][1]['json'], {'q': 'bolt'})
        self.assertEqual(calls[0][1]['headers']['Referer'], 'https://example.com/shop')


class RequestCodeAdditions(unittest.TestCase):
    @staticmethod
    def fake():
        calls = []

        def make(verb):
            def call(*args, **kwargs):
                calls.append((verb, args, kwargs))
                return types.SimpleNamespace(
                    raise_for_status=lambda: None, json=lambda: {'ok': 1}, text='<html>page</html>')
            return call

        return types.SimpleNamespace(get=make('get'), post=make('post')), calls

    def test_page_load_defines_the_document_variable(self):
        snippet = request_code.generate_page_load('https://example.com/shop?page=2', user_agent='UA/1')
        module, calls = self.fake()
        namespace = {'requests': module}
        exec(snippet.code, namespace)
        self.assertEqual(namespace['html'], '<html>page</html>')
        self.assertEqual(calls[0][2]['headers'], {'User-Agent': 'UA/1'})
        self.assertEqual(calls[0][2]['params'], {'page': '2'})
        self.assertEqual(snippet.result_name, 'html')

    def test_text_name_for_a_non_json_response(self):
        spec = request_code.RequestSpec(method='GET', url='https://example.com/fragment')
        snippet = request_code.generate_request_code(spec, text_name='html')
        module, _calls = self.fake()
        namespace = {'requests': module}
        exec(snippet.code, namespace)
        self.assertEqual(namespace['html'], '<html>page</html>')

    def test_urlencoded_body_kind_without_a_content_type_header(self):
        spec = request_code.RequestSpec(
            method='POST', url='https://example.com/f', body='a=1&b=two+words', body_kind='urlencoded')
        module, calls = self.fake()
        exec(request_code.generate_request_code(spec).code, {'requests': module})
        self.assertEqual(calls[0][2]['data'], {'a': '1', 'b': 'two words'})

    def test_multipart_body_kind_uses_files(self):
        spec = request_code.RequestSpec(
            method='POST', url='https://example.com/f', body='a=1&b=two+words', body_kind='multipart')
        module, calls = self.fake()
        exec(request_code.generate_request_code(spec).code, {'requests': module})
        self.assertEqual(calls[0][2]['files'], {'a': (None, '1'), 'b': (None, 'two words')})

    def test_plain_text_body_stays_raw(self):
        spec = request_code.RequestSpec(method='POST', url='https://example.com/f', body='just some text')
        module, calls = self.fake()
        exec(request_code.generate_request_code(spec).code, {'requests': module})
        self.assertEqual(calls[0][2]['data'], 'just some text')


class HookScript(unittest.TestCase):
    def test_placeholders_are_filled(self):
        source = capture_hook.hook_source()
        for placeholder in ('__MAX_BODY__', '__MAX_QUEUED__', '__BRIDGE__'):
            self.assertNotIn(placeholder, source)

        self.assertIn(f'channel.objects.{capture_hook.BRIDGE_NAME}', source)
        self.assertIn(str(capture_hook.MAX_BODY_CHARS), source)


class SoftWrapMapping(unittest.TestCase):
    pages = {
        'listing': sample_pages.LISTING,
        'minified': sample_pages.MINIFIED,
        'crlf': sample_pages.WINDOWS_LINE_ENDINGS,
        'repeated': sample_pages.REPEATED,
        'empty': '',
        'no newline': 'abc',
        'trailing newline': 'abc\n',
        'trailing crlf': 'abc\r\n',
        'blank lines': '\n\n\r\n\n',
        'long unbroken': 'x' * 1000,
        'long with spaces': ('word ' * 400).strip(),
    }

    def test_lines_are_never_longer_than_the_width(self):
        for name, text in self.pages.items():
            with self.subTest(page=name):
                wrapped = soft_wrap.SoftWrap(text, width=80)
                self.assertTrue(all(len(line) <= 80 for line in wrapped.display.split('\n')))

    def test_no_carriage_returns_are_displayed(self):
        wrapped = soft_wrap.SoftWrap(sample_pages.WINDOWS_LINE_ENDINGS)
        self.assertNotIn('\r', wrapped.display)

    def test_every_visible_character_round_trips_exactly(self):
        for name, text in self.pages.items():
            wrapped = soft_wrap.SoftWrap(text, width=80)
            for original in range(len(text)):
                if text[original].isspace():
                    continue

                with self.subTest(page=name, index=original):
                    start, end = wrapped.to_display(original, original + 1)
                    self.assertEqual(wrapped.display[start:end], text[original])
                    self.assertEqual(wrapped.to_original(start, end), (original, original + 1))

    def test_ranges_keep_their_visible_content(self):
        generator = random.Random(12345)
        for name, text in self.pages.items():
            if len(text) < 4:
                continue

            wrapped = soft_wrap.SoftWrap(text, width=60)
            for _attempt in range(300):
                start = generator.randrange(len(text) - 1)
                end = generator.randrange(start + 1, min(len(text), start + 400) + 1)
                with self.subTest(page=name, start=start, end=end):
                    display_start, display_end = wrapped.to_display(start, end)
                    shown = ''.join(wrapped.display[display_start:display_end].split())
                    self.assertEqual(shown, ''.join(text[start:end].split()))

    def test_selection_made_in_the_display_maps_back_to_the_original_text(self):
        text = sample_pages.MINIFIED
        wrapped = soft_wrap.SoftWrap(text, width=60)
        generator = random.Random(99)
        for _attempt in range(300):
            start = generator.randrange(len(wrapped.display) - 1)
            end = generator.randrange(start + 1, min(len(wrapped.display), start + 300) + 1)
            original_start, original_end = wrapped.to_original(start, end)
            self.assertEqual(''.join(text[original_start:original_end].split()),
                             ''.join(wrapped.display[start:end].split()))

    def test_width_must_be_sensible(self):
        with self.assertRaises(ValueError):
            soft_wrap.SoftWrap('abc', width=5)

    def test_breaks_prefer_tag_boundaries(self):
        text = '<p>' + 'x' * 30 + '</p><p>' + 'y' * 30 + '</p>'
        wrapped = soft_wrap.SoftWrap(text, width=50)
        first_line = wrapped.display.split('\n')[0]
        self.assertTrue(first_line.endswith('>'), first_line)


class ScriptBuilder(unittest.TestCase):
    def snippet(self, **overrides):
        values = {'code': 'x = 1', 'description': 'd', 'imports': [], 'warnings': []}
        values.update(overrides)
        return snippets.Snippet(**values)

    def test_block_puts_warnings_above_the_code(self):
        block = script_builder.snippet_block(self.snippet(warnings=['Something to check.']))
        self.assertEqual(block, '# NOTE: Something to check.\nx = 1')

    def test_long_warnings_wrap(self):
        block = script_builder.snippet_block(self.snippet(warnings=['word ' * 60]))
        self.assertTrue(all(len(line) <= 100 for line in block.split('\n')))
        self.assertTrue(all(line.startswith('#') for line in block.split('\n')[:-1]))

    def test_imports_into_an_empty_script(self):
        text = script_builder.import_text('', ['import re'])
        self.assertEqual(text, 'import re\n')
        self.assertEqual(script_builder.import_position(''), 0)

    def test_imports_go_after_existing_imports(self):
        script = 'import os\nimport sys\n\nx = 1\n'
        self.assertEqual(script_builder.import_position(script), 2)
        self.assertEqual(script_builder.import_text(script, ['import re']), 'import re\n')

    def test_imports_that_are_already_there_are_not_repeated(self):
        script = 'import re\nfrom bs4 import BeautifulSoup\n'
        self.assertEqual(script_builder.import_text(script, ['import re', 'from bs4 import BeautifulSoup']), '')

    def test_duplicates_in_the_request_are_collapsed(self):
        self.assertEqual(script_builder.missing_imports('', ['import re', 'import re']), ['import re'])

    def test_imports_go_below_a_docstring_and_comments(self):
        script = '#!/usr/bin/env python\n# header\n"""Scrape things.\n\nMore text.\n"""\n\nx = 1\n'
        position = script_builder.import_position(script)
        self.assertEqual(script.split('\n')[position - 1], '"""')

    def test_one_line_docstring(self):
        script = '"""Scrape things."""\nx = 1\n'
        self.assertEqual(script_builder.import_position(script), 1)

    def test_first_imports_are_set_off_from_code(self):
        script = '"""Doc."""\nx = 1\n'
        self.assertEqual(script_builder.import_text(script, ['import re']), 'import re\n\n')

    def test_applying_the_edits_gives_a_working_script(self):
        script = '"""Doc."""\nimport os\n\nvalue = os.sep\n'
        text = script_builder.import_text(script, ['import re'])
        lines = script.split('\n')
        lines.insert(script_builder.import_position(script), text.rstrip('\n'))
        result = '\n'.join(lines)
        compile(result, '<script>', 'exec')
        self.assertIn('import os\nimport re\n', result)


class JsonExtraction(unittest.TestCase):
    sample = {
        'total': 2,
        'items': [
            {'name': 'Widget', 'price': 9.99, 'tags': ['a', 'b']},
            {'name': 'Gadget', 'price': 19.99, 'tags': ['c']},
        ],
    }

    def run_code(self, code: str) -> dict:
        namespace = {'data': self.sample}
        exec(code, namespace)
        return namespace

    def test_suggest_name(self):
        self.assertEqual(json_extract.suggest_name(('items', 0, 'price')), 'price')
        self.assertEqual(json_extract.suggest_name(('items', 0, 'unit-price')), 'unit_price')
        self.assertEqual(json_extract.suggest_name(('items', 0, 'tags', 1)), 'tags_item')
        self.assertEqual(json_extract.suggest_name(('class',)), 'class_')
        self.assertEqual(json_extract.suggest_name(('3d',)), '_3d')
        self.assertEqual(json_extract.suggest_name((0,)), 'value')

    def test_flat_extraction(self):
        code = json_extract.generate_extraction_code([(('total',), 'total'), (('items', 1, 'name'), 'second')])
        namespace = self.run_code(code)
        self.assertEqual((namespace['total'], namespace['second']), (2, 'Gadget'))

    def test_two_fields_of_one_element_become_a_loop(self):
        code = json_extract.generate_extraction_code(
            [(('items', 0, 'name'), 'name'), (('items', 0, 'price'), 'price')])
        self.assertIn('for item in data[\'items\']', code)
        self.assertEqual(self.run_code(code)['results'], [
            {'name': 'Widget', 'price': 9.99}, {'name': 'Gadget', 'price': 19.99}])

    def test_every_item_for_a_single_field(self):
        code = json_extract.generate_extraction_code([(('items', 0, 'price'), 'price')], every_item=True)
        self.assertEqual(self.run_code(code)['price_values'], [9.99, 19.99])

    def test_every_item_with_nested_array_takes_the_innermost(self):
        code = json_extract.generate_extraction_code([(('items', 0, 'tags', 1), 'tag')], every_item=True)
        self.assertIn("data['items'][0]['tags']", code)
        self.assertEqual(self.run_code(code)['tag_values'], ['a', 'b'])

    def test_every_item_needs_an_array(self):
        with self.assertRaises(ValueError):
            json_extract.generate_extraction_code([(('total',), 'total')], every_item=True)

    def test_every_item_needs_one_shared_array(self):
        with self.assertRaises(ValueError):
            json_extract.generate_extraction_code(
                [(('items', 0, 'name'), 'a'), (('other', 0, 'name'), 'b')], every_item=True)

    def test_has_array_step(self):
        self.assertTrue(json_extract.has_array_step(('items', 0, 'price')))
        self.assertFalse(json_extract.has_array_step(('total',)))

    def test_snippet_for(self):
        snippet = json_extract.snippet_for([(('items', 0, 'price'), 'price')], every_item=True)
        self.assertEqual(snippet.result_name, 'price')
        self.assertIn('every item', snippet.description)

    def test_describe_asks_the_claude_package_and_strips_the_fence(self):
        asked = {}

        class FakeClient:
            def ask(self, prompt, **options):
                asked['prompt'] = prompt
                asked['options'] = options
                return types.SimpleNamespace(text='```python\nresults = [item["name"] for item in data["items"]]\n```')

        code = json_extract.describe(self.sample, 'every item name', client=FakeClient())

        self.assertEqual(code, 'results = [item["name"] for item in data["items"]]')
        self.assertIn('every item name', asked['prompt'])
        self.assertIn('Widget', asked['prompt'])
        self.assertIn('bound to the variable `data`', asked['options']['system'])
        self.assertEqual(self.run_code(code)['results'], ['Widget', 'Gadget'])

    def test_code_fence_is_stripped(self):
        self.assertEqual(json_extract._strip_code_fence('```python\nx = 1\n```'), 'x = 1')
        self.assertEqual(json_extract._strip_code_fence('x = 1'), 'x = 1')


if __name__ == '__main__':
    unittest.main()
