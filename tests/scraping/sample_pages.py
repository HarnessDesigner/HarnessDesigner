# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Pages the scraping tests run the generated code against."""

import re

LISTING = '''<!DOCTYPE html>
<html>
  <head>
    <title>Parts - Example</title>
  </head>
  <body>
    <div id="results">
      <div class="item" data-id="1">
        <a class="name" href="/p/1">Widget</a>
        <span class="price">$9.99</span>
        <span class="stock">In stock</span>
      </div>
      <div class="item" data-id="2">
        <a class="name" href="/p/2">Gadget</a>
        <span class="price">$19.99</span>
        <span class="stock">In stock</span>
      </div>
      <div class="item" data-id="3">
        <a class="name" href="/p/3">Doohickey</a>
        <span class="price css-1x2y3z4">$29.99</span>
        <span class="stock">Backordered</span>
      </div>
    </div>
    <p>Prices &amp; availability change daily.</p>
  </body>
</html>
'''

# The same page the way most sites actually serve it: one line, no indentation.
MINIFIED = re.sub(r'>\s+<', '><', LISTING.replace('\n', ' ')).strip()

WINDOWS_LINE_ENDINGS = LISTING.replace('\n', '\r\n')

# Identical rows on purpose: every selection here is ambiguous.
REPEATED = '''<table>
<tr><td>Name</td><td>Qty</td></tr>
<tr><td>Bolt</td><td>10</td></tr>
<tr><td>Nut</td><td>10</td></tr>
<tr><td>Washer</td><td>10</td></tr>
</table>
'''

ALL_PAGES = {
    'listing': LISTING,
    'minified': MINIFIED,
    'crlf': WINDOWS_LINE_ENDINGS,
    'repeated': REPEATED,
}


def text_nodes(document: str) -> list[tuple[int, int]]:
    """(start, end) of every non-blank piece of text between two tags."""
    spans = []
    for found in re.finditer(r'>([^<>]+)<', document):
        text = found.group(1)
        if not text.strip():
            continue

        stripped_start = found.start(1) + (len(text) - len(text.lstrip()))
        stripped_end = found.end(1) - (len(text) - len(text.rstrip()))
        spans.append((stripped_start, stripped_end))

    return spans
