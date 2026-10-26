# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Assembles the single, self-contained HTML dump file.

A static shell (styles + a small vanilla-JS tree viewer, no external
dependencies) wraps a streamed-in ``<script>`` block holding one JSON
record per line (NDJSON) -- the meta record first, then one node record
per captured object, written and flushed as the walk produces them. That
means the file on disk stays openable in a browser (missing only its
closing tags) even if the walk itself dies partway through.

The viewer never pre-renders a node's children: a node's row is built once
collapsed, and its children are only materialized into the DOM when the
user expands it, then discarded again on collapse, by looking the node
back up in the in-memory id->record map built from the embedded NDJSON at
page load. A ``ref`` child (an already-captured, deduplicated object) is
rendered exactly like a normal nested object -- expanding it just looks up
its target id in the same map.
"""

from __future__ import annotations

from .json_writer import dumps_for_script_embed
from ... import check_types as _check_types

_HEAD = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>crash_dump</title>
<style>
body { font-family: Consolas, "Courier New", monospace; font-size: 13px; margin: 12px; background: #1e1e1e; color: #d4d4d4; }
#meta { margin-bottom: 10px; color: #9da5b4; }
.node { margin-left: 16px; }
.node-header { cursor: pointer; padding: 1px 4px; border-radius: 3px; }
.node-header:hover { background: #2d3f52; }
.toggle { display: inline-block; width: 14px; font-weight: bold; color: #5eb3f5; }
.children { margin-left: 4px; }
.leaf { margin-left: 16px; padding: 1px 4px; border-radius: 3px; }
.leaf-line { white-space: pre; }
.leaf.error .leaf-line { color: #ff6b6b; }
.tb-toggle { cursor: pointer; color: #5eb3f5; font-size: 11px; margin-left: 6px; }
.traceback { background: #262626; border: 1px solid #3c3c3c; padding: 6px; margin: 4px 0 4px 16px; white-space: pre; overflow-x: auto; color: #d4d4d4; }
.missing { color: #ff6b6b; font-style: italic; }
.children > *:nth-child(even), #app > *:nth-child(even) { background: #272727; }
</style>
</head>
<body>
<div id="meta">Loading dump...</div>
<div id="app"></div>
<script type="application/json" id="dump-data">
"""

_TAIL = """\
</script>
<script>
(function () {
  var raw = document.getElementById('dump-data').textContent;
  var lines = raw.split('\\n').filter(function (l) { return l.trim().length > 0; });
  var meta = null;
  var nodesById = {};
  lines.forEach(function (line) {
    var record = JSON.parse(line);
    if (record.kind === 'meta') {
      meta = record;
    } else {
      nodesById[record.id] = record;
    }
  });

  var metaBox = document.getElementById('meta');
  var app = document.getElementById('app');

  function childValueText(child) {
    if (child.kind === 'value') return JSON.stringify(child.value);
    if (child.kind === 'ref') return '(object) #' + child.ref;
    if (child.kind === 'error') return '\\u26A0 ' + child.error.type + ': ' + child.error.message;
    return '';
  }

  function buildChildRow(child) {
    if (child.kind === 'ref') {
      return buildNodeRow(child.ref, child.name);
    }
    if (child.kind === 'container') {
      return buildContainerRow(child);
    }
    var row = document.createElement('div');
    row.className = 'leaf' + (child.kind === 'error' ? ' error' : '');
    var line = document.createElement('div');
    line.className = 'leaf-line';
    line.textContent = child.name + ': ' + childValueText(child);
    row.appendChild(line);
    if (child.kind === 'error' && child.error && child.error.traceback) {
      var tbToggle = document.createElement('span');
      tbToggle.className = 'tb-toggle';
      tbToggle.textContent = '[traceback]';
      var pre = document.createElement('pre');
      pre.className = 'traceback';
      pre.style.display = 'none';
      pre.textContent = child.error.traceback;
      tbToggle.addEventListener('click', function () {
        pre.style.display = pre.style.display === 'none' ? 'block' : 'none';
      });
      line.appendChild(tbToggle);
      row.appendChild(pre);
    }
    return row;
  }

  function buildContainerRow(child) {
    var row = document.createElement('div');
    row.className = 'node';

    var header = document.createElement('div');
    header.className = 'node-header';
    var toggle = document.createElement('span');
    toggle.className = 'toggle';
    toggle.textContent = '+';
    header.appendChild(toggle);
    var text = document.createElement('span');
    var count = child.items.length;
    text.textContent = child.name + ': (' + child.container_type + ', ' + count + (count === 1 ? ' item)' : ' items)');
    header.appendChild(text);
    row.appendChild(header);

    var childrenBox = document.createElement('div');
    childrenBox.className = 'children';
    childrenBox.style.display = 'none';
    row.appendChild(childrenBox);

    var expanded = false;
    header.addEventListener('click', function () {
      expanded = !expanded;
      if (expanded) {
        toggle.textContent = '-';
        childrenBox.style.display = 'block';
        child.items.forEach(function (item) {
          childrenBox.appendChild(buildChildRow(item));
        });
      } else {
        toggle.textContent = '+';
        childrenBox.style.display = 'none';
        childrenBox.textContent = '';
      }
    });

    return row;
  }

  function buildNodeRow(nodeId, nameLabel) {
    var node = nodesById[nodeId];
    var row = document.createElement('div');
    row.className = 'node';

    var header = document.createElement('div');
    header.className = 'node-header';
    var toggle = document.createElement('span');
    toggle.className = 'toggle';
    toggle.textContent = '+';
    header.appendChild(toggle);
    var text = document.createElement('span');
    var prefix = nameLabel ? nameLabel + ': ' : '';
    text.className = node ? '' : 'missing';
    text.textContent = prefix + (node ? node.label : '(missing #' + nodeId + ')');
    header.appendChild(text);
    row.appendChild(header);

    var childrenBox = document.createElement('div');
    childrenBox.className = 'children';
    childrenBox.style.display = 'none';
    row.appendChild(childrenBox);

    var expanded = false;
    header.addEventListener('click', function () {
      expanded = !expanded;
      if (expanded) {
        toggle.textContent = '-';
        childrenBox.style.display = 'block';
        if (node && node.children) {
          node.children.forEach(function (child) {
            childrenBox.appendChild(buildChildRow(child));
          });
        }
      } else {
        toggle.textContent = '+';
        childrenBox.style.display = 'none';
        childrenBox.textContent = '';
      }
    });

    return row;
  }

  if (meta) {
    var summary = document.createElement('span');
    summary.textContent = (meta.dump_kind || '') + ' dump, trigger severity ' +
      meta.trigger_severity + ', ' + (meta.timestamp || '');
    metaBox.textContent = '';
    metaBox.appendChild(summary);
    if (meta.exception) {
      var excLine = document.createElement('div');
      excLine.className = 'leaf error';
      var excText = document.createElement('div');
      excText.className = 'leaf-line';
      excText.textContent = '\\u26A0 triggered by ' + meta.exception.type + ': ' + meta.exception.message;
      excLine.appendChild(excText);
      if (meta.exception.traceback) {
        var excTbToggle = document.createElement('span');
        excTbToggle.className = 'tb-toggle';
        excTbToggle.textContent = '[traceback]';
        var excPre = document.createElement('pre');
        excPre.className = 'traceback';
        excPre.style.display = 'none';
        excPre.textContent = meta.exception.traceback;
        excTbToggle.addEventListener('click', function () {
          excPre.style.display = excPre.style.display === 'none' ? 'block' : 'none';
        });
        excText.appendChild(excTbToggle);
        excLine.appendChild(excPre);
      }
      metaBox.appendChild(excLine);
    }
  }
  if (meta && meta.roots) {
    meta.roots.forEach(function (rootId) {
      app.appendChild(buildNodeRow(rootId, null));
    });
  }
})();
</script>
</body>
</html>
"""


class HtmlDumpWriter:
    """
    Streaming writer for one dump. Use as a context manager:

        with HtmlDumpWriter(path) as writer:
            writer.write_meta({...})
            for node in walked_nodes:
                writer.write_node(node)
    """

    @_check_types.do
    def __init__(self, path: str):
        self._path = path
        self._file = None

    @_check_types.do
    def __enter__(self) -> 'HtmlDumpWriter':
        self._file = open(self._path, 'w', encoding='utf-8', newline='\n')
        self._file.write(_HEAD)
        return self

    @_check_types.do
    def write_meta(self, meta: dict) -> None:
        self._write_line({**meta, 'kind': 'meta'})

    @_check_types.do
    def write_node(self, node: dict) -> None:
        self._write_line({**node, 'kind': 'node'})

    @_check_types.do
    def _write_line(self, record: dict) -> None:
        self._file.write(dumps_for_script_embed(record))
        self._file.write('\n')
        self._file.flush()

    @_check_types.do
    def __exit__(self, exc_type, exc_value, exc_tb) -> bool:
        try:
            self._file.write(_TAIL)
        finally:
            self._file.close()
        return False
