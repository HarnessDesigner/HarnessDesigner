# harness_designer/scraping/assistant_tools.py

make_tools() — the four tools Claude can call to check a selector or JSON path against the real page (find_text, test_css_selector, test_xpath, inspect_json); each runs on a worker thread, not the GUI thread.

Nested loops (cost grows with the product of the sizes; check the sizes are small): `run_css` (lines 122-142, depth 2).

Status: static read of the code only. Nothing here has been profiled.
