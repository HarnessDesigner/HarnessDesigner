# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Right-click an element in the live page -> a selector for it.

The page side (:data:`PICK_SCRIPT`) works out a CSS selector for the
element under the pointer in the browser's own DOM, using the same rules as
:mod:`~harness_designer.scraping.html_locate` (skip generated class names,
pin only the level that needs ``:nth-of-type``). The Python side turns what
it reports into a snippet.

What comes back is data from the page being browsed, so it is validated
rather than trusted, and only ever reaches generated code as a string
literal.
"""

import json

from . import snippets as _snippets
from .. import check_types as _check_types

# Longest selector / text accepted from the page.
_MAX_SELECTOR_CHARS = 2000
_MAX_TEXT_CHARS = 500

RENDERED_WARNING = (
    'This selector was built from the rendered page, after JavaScript ran. A script that downloads the page '
    'with requests sees the original HTML, which may not contain this element -- check it in the Source tab '
    '("As served").')

# %X% and %Y% are filled with the click position in CSS pixels.
PICK_SCRIPT = r'''
(function (x, y) {
  var element = document.elementFromPoint(x, y);
  if (!element) { return null; }

  function stable(name) {
    return !/\d{3,}|^(css|sc|jsx|styled|emotion)-|^_|^[A-Za-z0-9_-]{24,}$/.test(name);
  }
  function segment(e) {
    var tag = e.tagName.toLowerCase();
    if (e.id && stable(e.id) && !/^\d+$/.test(e.id)) { return '#' + CSS.escape(e.id); }
    var classes = Array.prototype.filter.call(e.classList, stable);
    if (classes.length) {
      return tag + classes.map(function (c) { return '.' + CSS.escape(c); }).join('');
    }
    var keyed = ['itemprop', 'data-testid', 'data-test', 'data-qa', 'name'];
    for (var i = 0; i < keyed.length; i++) {
      var value = e.getAttribute(keyed[i]);
      if (value && stable(value)) { return tag + '[' + keyed[i] + '=' + JSON.stringify(value) + ']'; }
    }
    return tag;
  }
  function position(e) {
    var n = 1;
    for (var s = e.previousElementSibling; s; s = s.previousElementSibling) {
      if (s.tagName === e.tagName) { n++; }
    }
    return n;
  }
  function unique(target) {
    var chain = [];
    for (var n = target; n && n.nodeType === 1; n = n.parentElement) { chain.push(n); }
    for (var depth = 0; depth < chain.length; depth++) {
      for (var pin = 0; pin < 2; pin++) {
        var parts = [];
        for (var level = depth; level >= 0; level--) {
          var s = segment(chain[level]);
          if (pin && level === depth) { s += ':nth-of-type(' + position(chain[level]) + ')'; }
          parts.push(s);
        }
        var selector = parts.join(' > ');
        var found = document.querySelectorAll(selector);
        if (found.length === 1 && found[0] === target) { return selector; }
      }
    }
    return null;
  }

  var own = segment(element);
  var parent = element.parentElement;
  var similar = own;
  if (own === element.tagName.toLowerCase() && parent) { similar = segment(parent) + ' > ' + own; }

  return JSON.stringify({
    tag: element.tagName.toLowerCase(),
    selector: unique(element),
    similar: similar,
    text: (element.innerText || element.textContent || '').trim().slice(0, 500),
    href: element.getAttribute('href') || '',
    src: element.getAttribute('src') || ''
  });
})(%X%, %Y%)
'''


@_check_types.do
def pick_script(x: int, y: int) -> str:
    """:data:`PICK_SCRIPT` for a click at (*x*, *y*) CSS pixels."""
    return PICK_SCRIPT.replace('%X%', str(int(x))).replace('%Y%', str(int(y)))


@_check_types.do
def parse_pick(text: object) -> dict[str, str] | None:
    """The page's answer to :data:`PICK_SCRIPT` as a dict of strings, or
    ``None`` if it is missing or malformed."""
    if not isinstance(text, str):
        return None

    try:
        raw = json.loads(text)
    except ValueError:
        return None

    if not isinstance(raw, dict):
        return None

    result: dict[str, str] = {}
    for key in ('tag', 'selector', 'similar', 'text', 'href', 'src'):
        value = raw.get(key)
        if value is None:
            value = ''

        if not isinstance(value, str):
            return None

        result[key] = value

    if len(result['selector']) > _MAX_SELECTOR_CHARS or len(result['similar']) > _MAX_SELECTOR_CHARS:
        return None

    result['text'] = result['text'][:_MAX_TEXT_CHARS]
    return result


@_check_types.do
def pick_snippet(pick: dict[str, str], what: str = 'text', *, every_similar: bool = False,
                 doc_name: str = 'html', soup_name: str = 'soup', parser: str = 'lxml',
                 taken: set[str] | None = None) -> _snippets.Snippet:
    """Code that reads the picked element out of the downloaded page.

    :param what: ``'text'``, ``'href'`` or ``'src'``.
    :param every_similar: Use the broader selector and read every match.
    :raises ValueError: The pick has no usable selector or no such attribute.
    """
    if what not in ('text', 'href', 'src'):
        raise ValueError(f'cannot read "{what}" from an element')

    if what != 'text' and not pick.get(what):
        raise ValueError(f'the element has no "{what}" attribute')

    if every_similar:
        selector = pick['similar']
    else:
        selector = pick['selector']

    if not selector:
        raise ValueError('no selector could be built for that element')

    names = _snippets.Names(taken)
    literal = _snippets.python_literal(selector)

    lines: list[str] = []
    if taken is None or soup_name not in taken:
        lines.append(f'{soup_name} = BeautifulSoup({doc_name}, {_snippets.python_literal(parser)})')

    if every_similar:
        result = names.new('values')
        if what == 'text':
            read = 'element.get_text(strip=True)'
        else:
            read = f'element[{_snippets.python_literal(what)}]'

        lines.append(f'{result} = [{read} for element in {soup_name}.select({literal})]')
        description = f'Read every element matching {selector}'
    else:
        if what == 'text':
            result = names.new('value')
            read = '.get_text(strip=True)'
        else:
            result = names.new(what)
            read = f'[{_snippets.python_literal(what)}]'

        lines.append(f'{result} = {soup_name}.select_one({literal}){read}')
        description = f'Read the <{pick["tag"]}> element {selector}'

    return _snippets.Snippet(
        code='\n'.join(lines),
        description=description,
        imports=['from bs4 import BeautifulSoup'],
        warnings=[RENDERED_WARNING],
        result_name=result)
