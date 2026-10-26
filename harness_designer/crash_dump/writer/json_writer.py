# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
JSON serialization for one dump record, safe for embedding as the text
content of an inert ``<script>`` element.

A node/meta record is serialized on its own line (JSON Lines/NDJSON) so the
writer can stream and flush one record at a time instead of buffering a
whole dump in memory. The only escaping actually needed is neutralizing
``<`` so a literal ``</script`` can never appear in the output and end the
element early -- the embedding script tag is never executed as JavaScript
(see ``html_writer``), so the usual JS-string-literal escaping
(U+2028/U+2029) doesn't apply here. ``>`` and ``&`` are escaped too, as the
same blanket, cheap-to-apply convention Django's ``json_script`` uses,
rather than special-casing just the one sequence that matters today.

A captured float can genuinely be NaN/Infinity (degenerate geometry is
exactly the kind of thing a crash dump exists to surface) -- ``json.dumps``
silently emits those as the bare tokens ``NaN``/``Infinity``/``-Infinity``,
a non-standard Python extension its own ``json.loads`` accepts back but
which is not valid JSON and makes a real browser's ``JSON.parse`` reject
the entire line outright. Rather than lose the record (or the NaN/Infinity
information itself, by silently coercing to ``null``), every float is
sanitized to its quoted string form before serializing.
"""

from __future__ import annotations

import json
import math

from ... import check_types as _check_types

_SCRIPT_SAFE_ESCAPES = {
    ord('<'): '\\u003C',
    ord('>'): '\\u003E',
    ord('&'): '\\u0026',
}


@_check_types.do
def _json_safe(value):
    if isinstance(value, float):
        if math.isnan(value):
            return 'NaN'

        if math.isinf(value):
            return 'Infinity' if value > 0 else '-Infinity'

        return value

    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    return value


@_check_types.do
def dumps_for_script_embed(record: dict) -> str:
    safe_record = _json_safe(record)

    return json.dumps(safe_record,
                      separators=(',', ':')).translate(_SCRIPT_SAFE_ESCAPES)
