# harness_designer/scraping/capture_hook.py

The JavaScript injected into every page that records fetch/XMLHttpRequest calls and reports them through a QWebChannel object named bridge; also exposes window.__hdPageSource() (re-download the page without it showing up as a captured request).

Large literal data at import: `_SOURCE` (8 KB of source, line 31). It is built when the module is imported and stays resident for the whole session; load it lazily on first use if the feature is rarely opened.

Status: static read of the code only. Nothing here has been profiled.
