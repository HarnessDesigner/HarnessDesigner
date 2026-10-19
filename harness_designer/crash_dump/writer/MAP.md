## FILES

#### __init__.py

Re-exports `dumps_for_script_embed` (json_writer.py) and `HtmlDumpWriter` (html_writer.py).

#### html_writer.py

`HtmlDumpWriter` — a streaming context-manager writer for one dump file: writes a static HTML/CSS/JS shell
header on `__enter__`, then `write_meta(meta)`/`write_node(node)` each append one NDJSON line (via
`json_writer.dumps_for_script_embed`) inside a `<script type="application/json" id="dump-data">` block and
flush immediately, then the closing tail (a small vanilla-JS tree viewer, no external dependencies) is
written on `__exit__`. Because each line is written and flushed as the walk produces it, the file stays
openable in a browser (missing only its closing tags) even if the walk dies partway through. The viewer
never pre-renders a node's children — a node's row is built once collapsed, and children are only
materialized into the DOM when the user expands it (then discarded again on collapse) by looking the node
back up in the in-memory id→record map built from the embedded NDJSON at page load; a `ref` child is
rendered exactly like a normal nested object, expanding it just looks up its target id in the same map.

#### json_writer.py

`dumps_for_script_embed(record)` — JSON-serializes one dump record (a meta or node dict) onto a single
NDJSON line, safe for embedding as the text content of an inert `<script>` element: `<`/`>`/`&` are escaped
to `<`/`>`/`&` (the same blanket, cheap-to-apply convention Django's `json_script` uses) so a
literal `</script` can never appear in the output and end the element early — the embedding tag is never
executed as JavaScript, so the usual JS-string-literal escaping (U+2028/U+2029) doesn't apply here. A
captured float can genuinely be NaN/Infinity (degenerate geometry is exactly what a crash dump exists to
surface); rather than lose the record — or the NaN/Infinity information itself, by silently coercing to
`null` — `_json_safe()` sanitizes every float to its quoted string form (`'NaN'`/`'Infinity'`/`'-Infinity'`)
before serializing, since plain `json.dumps` would otherwise emit the bare, non-standard tokens that a real
browser's `JSON.parse` rejects outright.
