# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Every snippet action is checked by running the code it generates against
the document it was generated from: the code has to reproduce the selection.
"""

import html
import re
import types
import unittest

from tests import _bootstrap
from tests.scraping import sample_pages

snippets = _bootstrap.load('scraping.snippets')
html_locate = _bootstrap.load('scraping.html_locate')
request_code = _bootstrap.load('scraping.request_code')


def run(snippet, document: str, extra: dict | None = None) -> dict:
    """Execute a snippet's imports and code with ``html`` bound to *document*."""
    namespace = {'html': document}
    if extra:
        namespace.update(extra)

    for line in snippet.imports:
        exec(line, namespace)

    exec(compile(snippet.code, '<snippet>', 'exec'), namespace)
    return namespace


class SelectionHelpers(unittest.TestCase):
    def test_trim_selection(self):
        document = 'abc   hello world   xyz'
        start, end = snippets.trim_selection(document, 3, 20)
        self.assertEqual(document[start:end], 'hello world')

    def test_free_name(self):
        self.assertEqual(snippets.free_name('after', set()), 'after')
        self.assertEqual(snippets.free_name('after', {'after'}), 'after_2')
        self.assertEqual(snippets.free_name('after', {'after', 'after_2'}), 'after_3')

    def test_taken_names_works_on_unfinished_code(self):
        taken = snippets.taken_names('html = get()\nfor item in html.split(')
        self.assertTrue({'html', 'get', 'item', 'for', 'split'} <= taken)

    def test_result_name_avoids_taken(self):
        document = sample_pages.LISTING
        start = document.index('Price') if 'Price' in document else document.index('Widget')
        snippet = snippets.text_after(document, start, start + 3, taken={'after'})
        self.assertEqual(snippet.result_name, 'after_2')

    def test_bad_selection_is_rejected(self):
        with self.assertRaises(ValueError):
            snippets.text_after('abc', 2, 2)

        with self.assertRaises(ValueError):
            snippets.text_after('abc', 0, 9)


class EveryTextNode(unittest.TestCase):
    """The same checks over every piece of text in every sample page."""

    def each_selection(self):
        for page_name, document in sample_pages.ALL_PAGES.items():
            for start, end in sample_pages.text_nodes(document):
                yield page_name, document, start, end

    def test_text_after_reproduces_the_rest_of_the_document(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.text_after(document, start, end)
                self.assertEqual(run(snippet, document)['after'], document[end:])

    def test_text_before_reproduces_the_start_of_the_document(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.text_before(document, start, end)
                self.assertEqual(run(snippet, document)['before'], document[:start])

    def test_find_position(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.find_position(document, start, end)
                self.assertEqual(run(snippet, document)['position'], start)

    def test_find_position_at_end(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.find_position(document, start, end, at_end=True)
                self.assertEqual(run(snippet, document)['end'], end)

    def test_split_at_every_occurrence(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.split_at_every(document, start, end)
                self.assertEqual(run(snippet, document)['parts'], document.split(document[start:end]))

    def test_regex_capture_gets_the_selection(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.regex_capture(document, start, end)
                self.assertEqual(run(snippet, document)['value'], document[start:end])
                self.assertEqual(
                    [warning for warning in snippet.warnings if 'not the text' in warning or 'does not match' in warning],
                    [])

    def test_regex_all_includes_the_selection(self):
        for page_name, document, start, end in self.each_selection():
            with self.subTest(page=page_name, selected=document[start:end]):
                snippet = snippets.regex_all(document, start, end)
                self.assertIn(document[start:end], run(snippet, document)['values'])
                self.assertEqual([warning for warning in snippet.warnings if 'does not match' in warning], [])

    def test_between_two_consecutive_text_nodes(self):
        for page_name, document in sample_pages.ALL_PAGES.items():
            nodes = sample_pages.text_nodes(document)
            for (first_start, first_end), (second_start, second_end) in zip(nodes, nodes[1:]):
                with self.subTest(page=page_name, first=document[first_start:first_end]):
                    snippet = snippets.between(document, first_start, first_end, second_start, second_end)
                    self.assertEqual(run(snippet, document)['value'], document[first_end:second_start])

    def test_every_snippet_compiles(self):
        for page_name, document, start, end in self.each_selection():
            for build in (snippets.split_at_every, snippets.text_after, snippets.text_before,
                          snippets.find_position, snippets.regex_capture, snippets.regex_all):
                with self.subTest(page=page_name, action=build.__name__):
                    compile(build(document, start, end).code, '<snippet>', 'exec')


class AmbiguousSelections(unittest.TestCase):
    document = sample_pages.REPEATED

    def second_ten(self):
        first = self.document.index('10')
        second = self.document.index('10', first + 1)
        return second, second + 2

    def test_marker_is_grown_to_reach_the_selected_occurrence(self):
        start, end = self.second_ten()
        snippet = snippets.text_after(self.document, start, end)
        self.assertEqual(run(snippet, self.document)['after'], self.document[end:])
        self.assertTrue(any('extended' in warning for warning in snippet.warnings), snippet.warnings)

    def test_first_occurrence_is_used_and_flagged(self):
        start = self.document.index('10')
        snippet = snippets.text_after(self.document, start, start + 2)
        self.assertTrue(any('appears' in warning for warning in snippet.warnings), snippet.warnings)

    def test_regex_context_is_whole_tags(self):
        document = sample_pages.LISTING
        start = document.index('Gadget')
        snippet = snippets.regex_capture(document, start, start + len('Gadget'))
        self.assertIn(r'<a\s+class="name"\s+href="/p/2">(.*?)</a>', snippet.code)
        self.assertEqual(run(snippet, document)['value'], 'Gadget')

    def test_regex_for_a_later_row_still_finds_that_row(self):
        start = self.document.index('Washer')
        snippet = snippets.regex_capture(self.document, start, start + len('Washer'))
        self.assertEqual(run(snippet, self.document)['value'], 'Washer')

    def test_marker_is_not_cut_in_the_middle_of_a_word(self):
        document = 'alpha_beta gamma_beta delta_beta'
        start = document.rindex('beta')
        snippet = snippets.text_after(document, start, start + 4)
        self.assertEqual(run(snippet, document)['after'], '')
        for marker in re.findall(r"'([^']*)'", snippet.code):
            self.assertFalse(marker[0].isalnum() and document.index(marker) > 0
                             and document[document.index(marker) - 1].isalnum(), marker)


class MultiLineMarkers(unittest.TestCase):
    def test_multi_line_selection_gets_its_own_variable(self):
        document = sample_pages.LISTING
        start = document.index('<span class="price">$9.99</span>')
        end = document.index('In stock') + len('In stock')
        snippet = snippets.text_after(document, start, end)
        self.assertIn('marker = (', snippet.code)
        self.assertEqual(run(snippet, document)['after'], document[end:])

    def test_long_single_line_selection_gets_its_own_variable(self):
        document = 'x' * 10 + 'a very long marker that goes on and on and on well past the inline limit' + 'y' * 10
        start = 10
        end = len(document) - 10
        snippet = snippets.text_after(document, start, end)
        self.assertIn('marker = ', snippet.code)
        self.assertEqual(run(snippet, document)['after'], 'y' * 10)


class ElementSnippets(unittest.TestCase):
    def setUp(self):
        self.listing = sample_pages.LISTING

    def span(self, document: str, text: str) -> tuple[int, int]:
        start = document.index(text)
        return start, start + len(text)

    def test_element_found_in_every_page_layout(self):
        for page_name, document in sample_pages.ALL_PAGES.items():
            located = html_locate.LocatedDocument(document)
            for start, end in sample_pages.text_nodes(document):
                with self.subTest(page=page_name, selected=document[start:end]):
                    hit = located.element_at(start, end)
                    self.assertIsNotNone(hit)

                    wanted = ' '.join(html.unescape(document[start:end]).split())
                    self.assertIn(wanted, ' '.join(hit.tag.get_text().split()))

    def test_hit_is_the_innermost_element(self):
        start, end = self.span(self.listing, '$19.99')
        hit = html_locate.LocatedDocument(self.listing).element_at(start, end)
        self.assertEqual(hit.name, 'span')
        self.assertEqual(hit.tag['class'], ['price'])

    def test_text_after_a_closing_tag_belongs_to_the_parent(self):
        start, end = self.span(self.listing, 'Prices &amp; availability')
        hit = html_locate.LocatedDocument(self.listing).element_at(start, end)
        self.assertEqual(hit.name, 'p')

    def test_selection_spanning_two_elements_gives_their_parent(self):
        start = self.listing.index('Gadget')
        end = self.listing.index('$19.99') + len('$19.99')
        hit = html_locate.LocatedDocument(self.listing).element_at(start, end)
        self.assertEqual(hit.name, 'div')
        self.assertEqual(hit.tag['data-id'], '2')

    def test_css_text_on_every_text_node(self):
        for page_name, document in sample_pages.ALL_PAGES.items():
            located = html_locate.LocatedDocument(document)
            for start, end in sample_pages.text_nodes(document):
                selected = document[start:end]
                if '&' in selected:
                    continue

                with self.subTest(page=page_name, selected=selected):
                    snippet = html_locate.css_text(document, start, end, located=located)
                    value = run(snippet, document)['value']
                    self.assertIn(selected, value)
                    self.assertEqual(snippet.warnings, [], snippet.code)

    def test_css_text_picks_exactly_the_selected_item(self):
        start, end = self.span(self.listing, '$19.99')
        snippet = html_locate.css_text(self.listing, start, end)
        self.assertEqual(run(snippet, self.listing)['value'], '$19.99')

    def test_css_pins_only_the_level_that_needs_it(self):
        start, end = self.span(self.listing, '$19.99')
        snippet = html_locate.css_text(self.listing, start, end)
        self.assertIn("'div.item:nth-of-type(2) > span.price'", snippet.code)

    def test_xpath_pins_only_the_level_that_needs_it(self):
        start, end = self.span(self.listing, '$19.99')
        snippet = html_locate.xpath_text(self.listing, start, end)
        self.assertIn("'//div[@class=\"item\"][2]/span[@class=\"price\"]'", snippet.code)

    def test_machine_generated_class_names_are_not_used(self):
        start, end = self.span(self.listing, '$29.99')
        snippet = html_locate.css_text(self.listing, start, end)
        self.assertNotIn('css-1x2y3z4', snippet.code)
        self.assertEqual(run(snippet, self.listing)['value'], '$29.99')

    def test_css_all_returns_the_whole_column(self):
        start, end = self.span(self.listing, '$9.99')
        snippet = html_locate.css_all(self.listing, start, end)
        # The third price also carries a machine-generated class, which the
        # selector ignores, so it is still part of the column.
        self.assertEqual(run(snippet, self.listing)['values'], ['$9.99', '$19.99', '$29.99'])
        self.assertNotIn('css-1x2y3z4', snippet.code)

    def test_css_attribute(self):
        start, end = self.span(self.listing, '/p/2')
        snippet = html_locate.css_attribute(self.listing, start, end)
        self.assertEqual(run(snippet, self.listing)['href'], '/p/2')

    def test_css_attribute_needs_an_attribute(self):
        start, end = self.span(self.listing, '$9.99')
        with self.assertRaises(ValueError):
            html_locate.css_attribute(self.listing, start, end)

    def test_existing_soup_variable_is_reused(self):
        start, end = self.span(self.listing, '$9.99')
        snippet = html_locate.css_text(self.listing, start, end, taken={'soup', 'html'})
        self.assertNotIn('BeautifulSoup(', snippet.code)

    def test_xpath_text_on_every_text_node(self):
        for page_name, document in sample_pages.ALL_PAGES.items():
            located = html_locate.LocatedDocument(document)
            for start, end in sample_pages.text_nodes(document):
                selected = document[start:end]
                if '&' in selected:
                    continue

                with self.subTest(page=page_name, selected=selected):
                    snippet = html_locate.xpath_text(document, start, end, located=located)
                    self.assertIn(selected, run(snippet, document)['value'])
                    self.assertEqual(snippet.warnings, [], snippet.code)

    def test_xpath_attribute(self):
        start, end = self.span(self.listing, '/p/3')
        snippet = html_locate.xpath_attribute(self.listing, start, end)
        self.assertEqual(run(snippet, self.listing)['href'], '/p/3')

    def test_xpath_all(self):
        start, end = self.span(self.listing, 'Gadget')
        snippet = html_locate.xpath_all(self.listing, start, end)
        self.assertEqual(run(snippet, self.listing)['values'], ['Widget', 'Gadget', 'Doohickey'])

    def test_xpath_all_includes_elements_with_extra_classes(self):
        start, end = self.span(self.listing, '$9.99')
        snippet = html_locate.xpath_all(self.listing, start, end)
        self.assertEqual(run(snippet, self.listing)['values'], ['$9.99', '$19.99', '$29.99'])

    def test_xpath_falls_back_to_a_position_when_classes_cannot_separate(self):
        document = '<ul><li>one</li><li>two</li><li>three</li></ul>'
        start = document.index('two')
        snippet = html_locate.xpath_text(document, start, start + 3)
        self.assertEqual(run(snippet, document)['value'], 'two')

    def test_css_falls_back_to_a_position_when_classes_cannot_separate(self):
        document = '<ul><li>one</li><li>two</li><li>three</li></ul>'
        start = document.index('two')
        snippet = html_locate.css_text(document, start, start + 3)
        self.assertEqual(run(snippet, document)['value'], 'two')
        self.assertIn('nth-of-type', snippet.code)

    def test_html_parser_choice_is_honoured(self):
        start, end = self.span(self.listing, '$9.99')
        snippet = html_locate.css_text(self.listing, start, end, parser='html.parser')
        self.assertIn("'html.parser'", snippet.code)
        self.assertEqual(run(snippet, self.listing)['value'], '$9.99')

    def test_selection_outside_any_element_is_an_error(self):
        document = 'just text, no markup'
        with self.assertRaises(ValueError):
            html_locate.css_text(document, 0, 4)


class RequestCode(unittest.TestCase):
    @staticmethod
    def fake_requests():
        calls = []

        def make(verb):
            def call(*args, **kwargs):
                calls.append((verb, args, kwargs))
                return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'ok': True})
            return call

        module = types.SimpleNamespace(
            get=make('get'), post=make('post'), put=make('put'), delete=make('delete'),
            request=make('request'))
        return module, calls

    def execute(self, spec):
        snippet = request_code.generate_request_code(spec)
        module, calls = self.fake_requests()
        namespace = {'requests': module}
        exec(compile(snippet.code, '<snippet>', 'exec'), namespace)
        self.assertEqual(len(calls), 1)
        return snippet, calls[0]

    def test_get_with_query_and_headers(self):
        spec = request_code.RequestSpec(
            method='GET',
            url='https://example.com/api/items?page=2&sort=price&sort=name#frag',
            headers={
                'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest',
                'Cookie': 'session=SECRET', 'Authorization': 'Bearer SECRET', 'sec-ch-ua': '"x"',
                'Host': 'example.com', 'Content-Length': '0'},
            response_is_json=True)
        snippet, (verb, args, kwargs) = self.execute(spec)

        self.assertEqual(verb, 'get')
        self.assertEqual(args, ('https://example.com/api/items',))
        self.assertEqual(kwargs['params'], [('page', '2'), ('sort', 'price'), ('sort', 'name')])
        self.assertEqual(kwargs['headers'], {
            'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'})
        self.assertIn('timeout', kwargs)
        self.assertNotIn('SECRET', snippet.code)
        self.assertTrue(any('Cookie' in warning and 'Authorization' in warning for warning in snippet.warnings))
        self.assertEqual(snippet.result_name, 'data')

    def test_post_json_body(self):
        spec = request_code.RequestSpec(
            method='POST', url='https://example.com/api/search',
            headers={'Content-Type': 'application/json'}, body='{"q": "bolt", "filters": {"in_stock": true}}')
        _snippet, (verb, _args, kwargs) = self.execute(spec)
        self.assertEqual(verb, 'post')
        self.assertEqual(kwargs['json'], {'q': 'bolt', 'filters': {'in_stock': True}})

    def test_post_form_body(self):
        spec = request_code.RequestSpec(
            method='POST', url='https://example.com/search',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}, body='q=bolt+m6&page=1')
        _snippet, (_verb, _args, kwargs) = self.execute(spec)
        self.assertEqual(kwargs['data'], {'q': 'bolt m6', 'page': '1'})

    def test_unknown_method_uses_requests_request(self):
        spec = request_code.RequestSpec(method='PROPFIND', url='https://example.com/dav')
        _snippet, (verb, args, _kwargs) = self.execute(spec)
        self.assertEqual(verb, 'request')
        self.assertEqual(args[0], 'PROPFIND')

    def test_names_do_not_collide_with_the_script(self):
        spec = request_code.RequestSpec(method='GET', url='https://example.com/a?x=1')
        snippet = request_code.generate_request_code(spec, taken={'url', 'response', 'params'})
        self.assertIn('url_2', snippet.code)
        self.assertIn('response_2', snippet.code)
        self.assertIn('params_2', snippet.code)


if __name__ == '__main__':
    unittest.main()
