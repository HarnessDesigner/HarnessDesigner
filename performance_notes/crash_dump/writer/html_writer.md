# harness_designer/crash_dump/writer/html_writer.py

HtmlDumpWriter — a streaming context-manager writer for one dump file: writes a static HTML/CSS/JS shell header on __enter__, then write_meta(meta)/write_node(node) each append one NDJSON line (via json_writer.dumps_for_script_embed) inside a <script type="application/json" id="dump-data"> block and flush immediately, then the closing tail (a small vanilla-JS tree viewer, no external dependencies) is written on __exit__.

Large literal data at import: `_TAIL` (5 KB of source, line 56). It is built when the module is imported and stays resident for the whole session; load it lazily on first use if the feature is rarely opened.

Status: static read of the code only. Nothing here has been profiled.
