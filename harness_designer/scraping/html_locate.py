# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Element-based snippets: find the HTML element a selection sits in and
write a CSS selector or XPath for it.

Positions come from ``html.parser``, the one parser that records the exact
source position of every start tag. The element it finds is then looked up
again, by tag name and document order, in the tree the *generated code*
will use (``lxml`` by default), and the selector is built and checked
against that tree -- so what the snippet says is what the script gets,
whichever parser built the tree.
"""

import bisect
import html as _html
import re
from dataclasses import dataclass

import bs4
import lxml.html
import soupsieve

from . import snippets as _snippets
from .. import check_types as _check_types

VOID_ELEMENTS = frozenset({
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'meta', 'param', 'source', 'track', 'wbr'})

# Attributes worth keying a selector on when an element has no usable class.
_KEY_ATTRIBUTES = ('itemprop', 'data-testid', 'data-test', 'data-qa', 'name')

# Generated class names and ids (CSS-in-JS hashes, counters) change on every
# deploy; a selector built on one breaks the next day.
_UNSTABLE_NAME = re.compile(r'\d{3,}|^(css|sc|jsx|styled|emotion)-|^_|^[A-Za-z0-9_-]{24,}$')

_CLOSING_TAG = re.compile(r'</\s*([A-Za-z][\w:.-]*)\s*>')
_ATTRIBUTE = re.compile(
    r'''([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?''')
_MARKUP = re.compile(r'<[^>]*>')


@dataclass
class ElementHit:
    """The element a selection sits in.

    :ivar tag: The element in the ``html.parser`` tree.
    :ivar name: Its tag name.
    :ivar ordinal: Its index among all elements of that name, in document order.
    :ivar in_start_tag: The selection is inside the start tag's text.
    :ivar attribute: Name of the attribute whose value holds the selection, if any.
    """

    tag: bs4.Tag
    name: str
    ordinal: int
    in_start_tag: bool
    attribute: str | None


class LocatedDocument:
    """A document parsed once, ready to answer "which element is this
    offset in" for any number of selections."""

    @_check_types.do
    def __init__(self, document: str) -> None:
        self.document = document
        self._soups: dict[str, bs4.BeautifulSoup] = {}

        self._line_starts = [0]
        for newline in re.finditer('\n', document):
            self._line_starts.append(newline.end())

        self._starts: list[int] = []
        self._tags: list[bs4.Tag] = []
        self._ordinals: dict[int, int] = {}
        counts: dict[str, int] = {}

        soup = self.soup('html.parser')
        for tag in soup.find_all(True):
            if tag.sourceline is None or tag.sourcepos is None:
                continue

            self._starts.append(self._line_starts[tag.sourceline - 1] + tag.sourcepos)
            self._tags.append(tag)

            ordinal = counts.get(tag.name, 0)
            counts[tag.name] = ordinal + 1
            self._ordinals[id(tag)] = ordinal

    @_check_types.do
    def soup(self, parser: str) -> bs4.BeautifulSoup:
        """The document parsed with *parser*, parsed on first request."""
        cached = self._soups.get(parser)
        if cached is None:
            cached = bs4.BeautifulSoup(self.document, parser)
            self._soups[parser] = cached

        return cached

    @_check_types.do
    def element_at(self, start: int, end: int) -> ElementHit | None:
        """The innermost element holding the whole selection, or ``None``
        when the selection is outside every element."""
        first = self._owner(start)
        last = self._owner(end - 1)
        if first is None or last is None:
            return None

        tag = self._common_ancestor(first[0], last[0])
        if tag is None:
            return None

        attribute = None
        if first[1] and last[1] and first[0] is last[0]:
            attribute = self._attribute_at(tag, start, end)

        return ElementHit(
            tag=tag,
            name=tag.name,
            ordinal=self._ordinals[id(tag)],
            in_start_tag=first[1] and last[1] and first[0] is last[0],
            attribute=attribute)

    @_check_types.do
    def resolve(self, hit: ElementHit, parser: str) -> bs4.Tag | None:
        """The element *hit* describes, in the tree *parser* builds."""
        matches = self.soup(parser).find_all(hit.name)
        if hit.ordinal < len(matches):
            return matches[hit.ordinal]

        return None

    @_check_types.do
    def _owner(self, position: int) -> tuple[bs4.Tag, bool] | None:
        """The element the character at *position* belongs to, and whether
        that character is inside the element's start tag."""
        index = bisect.bisect_right(self._starts, position) - 1
        if index < 0:
            return None

        tag = self._tags[index]
        tag_start = self._starts[index]
        tag_end = self._start_tag_end(tag_start)
        if position < tag_end:
            return tag, True

        # Text after the start tag: it belongs to this element unless the
        # element has no content or has been closed since.
        current = tag
        start_tag_text = self.document[tag_start:tag_end]
        if tag.name in VOID_ELEMENTS or start_tag_text.endswith('/>'):
            current = tag.parent

        for closing in _CLOSING_TAG.finditer(self.document, tag_end, position):
            name = closing.group(1).lower()
            node = current
            while node is not None and node.name != name:
                node = node.parent

            if node is not None:
                current = node.parent

        if current is None or isinstance(current, bs4.BeautifulSoup):
            return None

        return current, False

    @_check_types.do
    def _start_tag_end(self, position: int) -> int:
        """Index just past the ``>`` that ends the start tag at *position*
        (a ``>`` inside a quoted attribute value does not count)."""
        quote = ''
        index = position + 1
        while index < len(self.document):
            char = self.document[index]
            if quote:
                if char == quote:
                    quote = ''
            elif char in ('"', "'"):
                quote = char
            elif char == '>':
                return index + 1

            index += 1

        return len(self.document)

    @_check_types.do
    def _common_ancestor(self, first: bs4.Tag, second: bs4.Tag) -> bs4.Tag | None:
        ancestors: set[int] = set()
        node = first
        while node is not None:
            ancestors.add(id(node))
            node = node.parent

        node = second
        while node is not None:
            if id(node) in ancestors:
                break

            node = node.parent

        if node is None or isinstance(node, bs4.BeautifulSoup):
            return None

        return node

    @_check_types.do
    def _attribute_at(self, tag: bs4.Tag, start: int, end: int) -> str | None:
        tag_start = self._starts[self._tags.index(tag)]
        tag_end = self._start_tag_end(tag_start)
        tag_text = self.document[tag_start:tag_end]

        for found in _ATTRIBUTE.finditer(tag_text):
            for group in (2, 3, 4):
                if found.group(group) is None:
                    continue

                value_start = tag_start + found.start(group)
                value_end = tag_start + found.end(group)
                if value_start <= start and end <= value_end:
                    return found.group(1).lower()

        return None


@_check_types.do
def is_stable_name(value: str) -> bool:
    """False for class names and ids that look machine generated."""
    return _UNSTABLE_NAME.search(value) is None


@_check_types.do
def css_segment(tag: bs4.Tag) -> str:
    """One compound selector for *tag*: ``#id``, ``tag.class``,
    ``tag[attr="value"]`` or just the tag name."""
    tag_id = tag.get('id')
    if isinstance(tag_id, str) and tag_id and is_stable_name(tag_id) and not tag_id.isdigit():
        return '#' + soupsieve.escape(tag_id)

    classes = [name for name in (tag.get('class') or []) if is_stable_name(name)]
    if classes:
        return tag.name + ''.join('.' + soupsieve.escape(name) for name in classes)

    for attribute in _KEY_ATTRIBUTES:
        value = tag.get(attribute)
        if isinstance(value, str) and value and is_stable_name(value):
            return f'{tag.name}[{attribute}={_snippets.python_literal(value)}]'

    return tag.name


@_check_types.do
def unique_css(soup: bs4.BeautifulSoup, target: bs4.Tag) -> str:
    """The shortest selector (built from the element's own classes and its
    ancestors) that matches *target* and nothing else in *soup*; if the
    classes alone cannot separate it from lookalikes, positions
    (``:nth-of-type``) are added."""
    chain: list[bs4.Tag] = []
    node = target
    while node is not None and not isinstance(node, bs4.BeautifulSoup):
        chain.append(node)
        node = node.parent

    # Add one ancestor at a time. When the plain chain still matches
    # lookalikes, pin just its top element to its position
    # (`div.item:nth-of-type(2) > span.price`) before reaching further up.
    for depth in range(len(chain)):
        for pin_top in (False, True):
            segments: list[str] = []
            for level in range(depth, -1, -1):
                segment = css_segment(chain[level])
                if pin_top and level == depth:
                    segment += f':nth-of-type({_position_among_same_name(chain[level])})'

                segments.append(segment)

            selector = ' > '.join(segments)
            if _selects_only(soup, selector, target):
                return selector

    # Nothing shorter separated it: pin every level to its position.
    pinned = [f'{element.name}:nth-of-type({_position_among_same_name(element)})' for element in reversed(chain)]
    return ' > '.join(pinned)


@_check_types.do
def similar_css(target: bs4.Tag) -> str:
    """A selector meant to match *target* and its lookalikes: its own
    segment, plus the parent's when the element has nothing but a name."""
    own = css_segment(target)
    parent = target.parent
    if own == target.name and parent is not None and not isinstance(parent, bs4.BeautifulSoup):
        return css_segment(parent) + ' > ' + own

    return own


@_check_types.do
def xpath_segment(element: lxml.html.HtmlElement, loose: bool = False) -> str:
    """One XPath step for *element* with a predicate on its id or classes.

    With *loose*, classes are always tested as whole words rather than by
    comparing the entire ``class`` attribute, so elements carrying extra
    classes (usually generated ones) still match.
    """
    tag = str(element.tag)
    tag_id = element.get('id')
    if tag_id and is_stable_name(tag_id) and not tag_id.isdigit():
        return f'{tag}[@id={_xpath_literal(tag_id)}]'

    class_attribute = element.get('class')
    if class_attribute:
        classes = [name for name in class_attribute.split() if is_stable_name(name)]
        if not loose and len(classes) == 1 and class_attribute.strip() == classes[0]:
            return f'{tag}[@class={_xpath_literal(classes[0])}]'

        if classes:
            tests = ''.join(
                f"[contains(concat(' ', normalize-space(@class), ' '), {_xpath_literal(' ' + name + ' ')})]"
                for name in classes)
            return tag + tests

    for attribute in _KEY_ATTRIBUTES:
        value = element.get(attribute)
        if value and is_stable_name(value):
            return f'{tag}[@{attribute}={_xpath_literal(value)}]'

    return tag


@_check_types.do
def unique_xpath(tree: lxml.html.HtmlElement, target: lxml.html.HtmlElement) -> str:
    """The shortest ``//`` path (steps with id/class predicates) that selects
    *target* and nothing else; the absolute path if none does."""
    chain: list[lxml.html.HtmlElement] = []
    node = target
    while node is not None:
        chain.append(node)
        node = node.getparent()

    for depth in range(len(chain)):
        for pin_top in (False, True):
            steps: list[str] = []
            for level in range(depth, -1, -1):
                step = xpath_segment(chain[level])
                if pin_top and level == depth:
                    step += f'[{_position_among_matching(chain[level], step)}]'

                steps.append(step)

            candidate = '//' + '/'.join(steps)
            if tree.xpath(candidate) == [target]:
                return candidate

    return tree.getroottree().getpath(target)


@_check_types.do
def similar_xpath(target: lxml.html.HtmlElement) -> str:
    own = xpath_segment(target, loose=True)
    parent = target.getparent()
    if own == str(target.tag) and parent is not None:
        return '//' + xpath_segment(parent, loose=True) + '/' + own

    return '//' + own


@_check_types.do
def css_text(document: str, start: int, end: int, *, doc_name: str = 'html', soup_name: str = 'soup',
             parser: str = 'lxml', taken: set[str] | None = None,
             located: LocatedDocument | None = None) -> _snippets.Snippet:
    """The text of the element holding the selection, by CSS selector."""
    names = _snippets.Names(taken)
    located, hit, target = _locate(document, start, end, parser, located)
    soup = located.soup(parser)

    selector = unique_css(soup, target)
    warnings = _verify_css(soup, selector, document[start:end], expect_one=True)
    result = names.new('value')

    lines = _soup_lines(taken, doc_name, soup_name, parser)
    lines.append(f'{result} = {soup_name}.select_one({_snippets.python_literal(selector)}).get_text(strip=True)')

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Select the <{hit.name}> element by CSS selector and take its text',
        imports=['from bs4 import BeautifulSoup'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def css_all(document: str, start: int, end: int, *, doc_name: str = 'html', soup_name: str = 'soup',
            parser: str = 'lxml', taken: set[str] | None = None,
            located: LocatedDocument | None = None) -> _snippets.Snippet:
    """The text of every element that looks like the one holding the selection."""
    names = _snippets.Names(taken)
    located, hit, target = _locate(document, start, end, parser, located)
    soup = located.soup(parser)

    selector = similar_css(target)
    warnings = _verify_css(soup, selector, document[start:end], expect_one=False)
    count = len(soup.select(selector))
    result = names.new('values')

    lines = _soup_lines(taken, doc_name, soup_name, parser)
    literal = _snippets.python_literal(selector)
    lines.append(f'{result} = [element.get_text(strip=True) for element in {soup_name}.select({literal})]')

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Select every similar <{hit.name}> element by CSS selector ({count} match(es))',
        imports=['from bs4 import BeautifulSoup'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def css_attribute(document: str, start: int, end: int, *, doc_name: str = 'html', soup_name: str = 'soup',
                  parser: str = 'lxml', taken: set[str] | None = None,
                  located: LocatedDocument | None = None) -> _snippets.Snippet:
    """The attribute value holding the selection (``href``, ``src``, ``data-id``...)."""
    names = _snippets.Names(taken)
    located, hit, target = _locate(document, start, end, parser, located)
    if hit.attribute is None:
        raise ValueError('the selection is not inside an attribute value')

    soup = located.soup(parser)
    selector = unique_css(soup, target)
    warnings = _verify_css(soup, selector, '', expect_one=True)
    result = names.new(re.sub(r'\W', '_', hit.attribute))

    lines = _soup_lines(taken, doc_name, soup_name, parser)
    lines.append(f'{result} = {soup_name}.select_one({_snippets.python_literal(selector)})'
                 f'[{_snippets.python_literal(hit.attribute)}]')

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Select the <{hit.name}> element by CSS selector and take its "{hit.attribute}" attribute',
        imports=['from bs4 import BeautifulSoup'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def xpath_text(document: str, start: int, end: int, *, doc_name: str = 'html', tree_name: str = 'tree',
               taken: set[str] | None = None, located: LocatedDocument | None = None) -> _snippets.Snippet:
    """The text of the element holding the selection, by XPath."""
    names = _snippets.Names(taken)
    located, hit = _locate_hit(document, start, end, located)
    tree = lxml.html.fromstring(document)
    target = _resolve_lxml(tree, hit)

    xpath = unique_xpath(tree, target)
    warnings = _verify_xpath(tree, xpath, document[start:end])
    result = names.new('value')

    lines = _tree_lines(taken, doc_name, tree_name)
    lines.append(f'{result} = {tree_name}.xpath({_snippets.python_literal(xpath)})[0].text_content().strip()')

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Select the <{hit.name}> element by XPath and take its text',
        imports=['import lxml.html'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def xpath_attribute(document: str, start: int, end: int, *, doc_name: str = 'html', tree_name: str = 'tree',
                    taken: set[str] | None = None, located: LocatedDocument | None = None) -> _snippets.Snippet:
    """The attribute value holding the selection, by XPath."""
    names = _snippets.Names(taken)
    located, hit = _locate_hit(document, start, end, located)
    if hit.attribute is None:
        raise ValueError('the selection is not inside an attribute value')

    tree = lxml.html.fromstring(document)
    target = _resolve_lxml(tree, hit)

    xpath = unique_xpath(tree, target) + '/@' + hit.attribute
    warnings = _verify_xpath(tree, xpath, '')
    result = names.new(re.sub(r'\W', '_', hit.attribute))

    lines = _tree_lines(taken, doc_name, tree_name)
    lines.append(f'{result} = {tree_name}.xpath({_snippets.python_literal(xpath)})[0]')

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Select the <{hit.name}> element by XPath and take its "{hit.attribute}" attribute',
        imports=['import lxml.html'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def xpath_all(document: str, start: int, end: int, *, doc_name: str = 'html', tree_name: str = 'tree',
              taken: set[str] | None = None, located: LocatedDocument | None = None) -> _snippets.Snippet:
    """The text of every element that looks like the one holding the selection, by XPath."""
    names = _snippets.Names(taken)
    located, hit = _locate_hit(document, start, end, located)
    tree = lxml.html.fromstring(document)
    target = _resolve_lxml(tree, hit)

    xpath = similar_xpath(target)
    found = tree.xpath(xpath)
    warnings: list[str] = []
    if target not in found:
        warnings.append('The XPath does not select the element holding your selection.')

    result = names.new('values')
    lines = _tree_lines(taken, doc_name, tree_name)
    lines.append(f'{result} = [element.text_content().strip() '
                 f'for element in {tree_name}.xpath({_snippets.python_literal(xpath)})]')

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=f'Select every similar <{hit.name}> element by XPath ({len(found)} match(es))',
        imports=['import lxml.html'],
        warnings=warnings,
        result_name=result)


@_check_types.do
def _locate_hit(document: str, start: int, end: int,
                located: LocatedDocument | None) -> tuple[LocatedDocument, ElementHit]:
    if not 0 <= start < end <= len(document):
        raise ValueError(f'selection {start}:{end} is not inside a document of {len(document)} characters')

    if located is None:
        located = LocatedDocument(document)

    hit = located.element_at(start, end)
    if hit is None:
        raise ValueError('the selection is not inside an element')

    return located, hit


@_check_types.do
def _locate(document: str, start: int, end: int, parser: str,
            located: LocatedDocument | None) -> tuple[LocatedDocument, ElementHit, bs4.Tag]:
    located, hit = _locate_hit(document, start, end, located)
    target = located.resolve(hit, parser)
    if target is None:
        raise ValueError(f'the element could not be found again with the "{parser}" parser')

    return located, hit, target


@_check_types.do
def _resolve_lxml(tree: lxml.html.HtmlElement, hit: ElementHit) -> lxml.html.HtmlElement:
    matches = list(tree.iter(hit.name))
    if hit.ordinal >= len(matches):
        raise ValueError(f'the <{hit.name}> element could not be found again by lxml')

    return matches[hit.ordinal]


@_check_types.do
def _soup_lines(taken: set[str] | None, doc_name: str, soup_name: str, parser: str) -> list[str]:
    """The line that builds the soup -- skipped when the script already has
    a variable of that name (it is assumed to be the soup)."""
    if taken is not None and soup_name in taken:
        return []

    return [f'{soup_name} = BeautifulSoup({doc_name}, {_snippets.python_literal(parser)})']


@_check_types.do
def _tree_lines(taken: set[str] | None, doc_name: str, tree_name: str) -> list[str]:
    if taken is not None and tree_name in taken:
        return []

    return [f'{tree_name} = lxml.html.fromstring({doc_name})']


@_check_types.do
def _selects_only(soup: bs4.BeautifulSoup, selector: str, target: bs4.Tag) -> bool:
    matches = soup.select(selector)
    return len(matches) == 1 and matches[0] is target


@_check_types.do
def _position_among_same_name(tag: bs4.Tag) -> int:
    """1-based index of *tag* among its parent's children of the same name
    (what ``:nth-of-type`` counts)."""
    position = 0
    for sibling in tag.parent.children:
        if isinstance(sibling, bs4.Tag) and sibling.name == tag.name:
            position += 1

        if sibling is tag:
            break

    return position


@_check_types.do
def _position_among_matching(element: lxml.html.HtmlElement, step: str) -> int:
    """1-based index of *element* among its parent's children that *step*
    selects (what a trailing ``[n]`` on that step counts)."""
    parent = element.getparent()
    if parent is None:
        return 1

    return parent.xpath('./' + step).index(element) + 1


@_check_types.do
def _xpath_literal(value: str) -> str:
    """An XPath string literal for *value* (XPath 1.0 has no escapes, so a
    value holding both kinds of quote goes through ``concat``)."""
    if '"' not in value:
        return f'"{value}"'

    if "'" not in value:
        return f"'{value}'"

    pieces = value.split('"')
    return 'concat(' + ", '\"', ".join(f'"{piece}"' for piece in pieces) + ')'


@_check_types.do
def _plain_text(selected: str) -> str:
    """The selection as the text a parser would see: tags dropped,
    entities decoded, whitespace collapsed."""
    return ' '.join(_html.unescape(_MARKUP.sub(' ', selected)).split())


@_check_types.do
def _verify_css(soup: bs4.BeautifulSoup, selector: str, selected: str, expect_one: bool) -> list[str]:
    warnings: list[str] = []
    found = soup.select(selector)
    if not found:
        warnings.append('The CSS selector matches nothing in the parsed document.')
        return warnings

    if expect_one and len(found) > 1:
        warnings.append(f'The CSS selector matches {len(found)} elements; select_one returns the first.')

    wanted = _plain_text(selected)
    if wanted:
        texts = [' '.join(element.get_text().split()) for element in found]
        if not any(wanted in text for text in texts):
            warnings.append('The matched element\'s text does not contain your selection.')

    return warnings


@_check_types.do
def _verify_xpath(tree: lxml.html.HtmlElement, xpath: str, selected: str) -> list[str]:
    warnings: list[str] = []
    found = tree.xpath(xpath)
    if not found:
        warnings.append('The XPath matches nothing in the parsed document.')
        return warnings

    if len(found) > 1:
        warnings.append(f'The XPath matches {len(found)} nodes; the code uses the first.')

    wanted = _plain_text(selected)
    if wanted:
        texts: list[str] = []
        for node in found:
            if isinstance(node, str):
                texts.append(' '.join(node.split()))
            else:
                texts.append(' '.join(node.text_content().split()))

        if not any(wanted in text for text in texts):
            warnings.append('The matched element\'s text does not contain your selection.')

    return warnings
