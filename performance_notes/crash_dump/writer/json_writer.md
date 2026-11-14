# harness_designer/crash_dump/writer/json_writer.py

dumps_for_script_embed(record) — JSON-serializes one dump record (a meta or node dict) onto a single NDJSON line, safe for embedding as the text content of an inert <script> element: </>/& are escaped to </>/& (the same blanket, cheap-to-apply convention Django's json_script uses) so a literal </script can never appear in the output and end the element early — the embedding tag is never executed as JavaScript, so the usual JS-string-literal escaping (U+2028/U+2029) doesn't apply here.

Cold path (67 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
