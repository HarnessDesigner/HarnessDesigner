# harness_designer/scraping/html_locate.py

LocatedDocument (source offset → enclosing element, built from html.parser positions; an element is re-found in generated code by tag name + document order in the tree) and the element actions (css_text, css_all, css_attribute, xpath_text, xpath_all, xpath_attribute). Selectors skip machine-generated class names and pin only the tree level that actually needs :nth-of-type.

Nested loops (cost grows with the product of the sizes; check the sizes are small): `unique_css` (lines 255-285, depth 3), `unique_xpath` (lines 334-357, depth 3), `LocatedDocument._owner` (lines 135-167, depth 2), `LocatedDocument._attribute_at` (lines 210-225, depth 2).

Status: static read of the code only. Nothing here has been profiled.
