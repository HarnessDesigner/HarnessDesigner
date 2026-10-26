# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Walks an object graph from one or more roots, producing one node dict
per captured object for the writer to serialize.

A node's own id is just ``id(obj)`` -- stable only for the lifetime of a
single walk, which is exactly the lifetime a ``$ref`` needs. Traversal is
breadth-first over an explicit queue (not recursion) so a cycle in the
object graph -- or a shared object reached from two different places --
is handled by the same mechanism: once an object's id has been seen, every
further encounter just emits a ``ref`` to it, and it is never re-queued or
re-walked.

Only attributes/properties covered by a passing capture group ever get
read (see ``registry.capture_groups_for``) -- nothing here falls back to
``repr()`` for a type with no schema and no registered renderer; it is
simply omitted. A value with no capture schema of its own is handed to
``render.iter_render_children`` (builtins, app-registered custom types,
and the library's own lazy stdlib/third-party extras); anything it
returns as a breakdown is inlined recursively, bounded in depth and size,
since dedup only matters for the app's own shared objects, not for
incidental small containers.
"""

import traceback
from collections import deque
from datetime import datetime, timezone

from .registry import capture_groups_for
from .render import iter_render_children
from .writer import HtmlDumpWriter
from .. import check_types as _check_types

_MAX_CONTAINER_DEPTH = 4
_MAX_CONTAINER_ITEMS = 50


@_check_types.do
def walk(roots, *, trigger_severity: int):
    """
    Yield one node dict per captured object reachable from ``roots``,
    in breadth-first discovery order.
    """

    to_visit = deque()
    seen_ids: set[int] = set()
    for root in roots:
        root_id = id(root)
        if root_id not in seen_ids:
            seen_ids.add(root_id)
            to_visit.append(root)

    while to_visit:
        obj = to_visit.popleft()

        yield _build_node(obj, trigger_severity, to_visit, seen_ids)


@_check_types.do
def dump_to_html(
    roots,
    *,
    trigger_severity: int,
    dump_kind: str,
    path: str,
    exception: dict | None = None,
) -> None:

    with HtmlDumpWriter(path) as writer:
        meta = {'dump_kind': dump_kind,
                'trigger_severity': trigger_severity,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'roots': [id(root) for root in roots]}

        if exception is not None:
            meta['exception'] = exception

        writer.write_meta(meta)
        for node in walk(roots, trigger_severity=trigger_severity):  # NOQA
            writer.write_node(node)


@_check_types.do
def _build_node(obj, trigger_severity: int,
                to_visit: deque, seen_ids: set[int]) -> dict:

    # Every object reaching here was either an explicitly-requested root
    # (which may have no schema at all, e.g. during schema rollout) or a
    # value _classify_value already confirmed is registered -- an
    # unregistered root still gets a bare node (id/type/label, no
    # children) rather than failing; "not registered == not dumped"
    # governs attributes, not whether a requested root shows up at all.
    children = []
    groups = capture_groups_for(type(obj)) or ()
    for group in groups:
        if trigger_severity > group.severity:
            continue

        for attr in group.attrs:
            if trigger_severity > attr.severity:
                continue

            try:
                value = getattr(obj, attr.name)
                child_entry = _classify_value(attr.name, value, to_visit, seen_ids, 0)
            except Exception as exc:
                children.append(_error_child(attr.name, attr.severity, exc))
                continue

            if child_entry is not None:
                children.append(child_entry)

    return {'id': id(obj),
            'type': f'{type(obj).__module__}.{type(obj).__qualname__}',
            'label': _label_for(obj),
            'children': children}


@_check_types.do
def _label_for(obj) -> str:
    return f'{type(obj).__qualname__} #{id(obj)}'


@_check_types.do
def _error_child(name: str, severity: int, exc: Exception) -> dict:
    formatted = ''.join(
        traceback.format_exception(type(exc), exc, exc.__traceback__))

    return {'name': name,
            'kind': 'error',
            'severity': severity,
            'error': {'type': type(exc).__name__,
                      'message': str(exc),
                      'traceback': formatted}}


@_check_types.do
def _classify_value(name: str, value,
                    to_visit: deque, seen_ids: set[int], depth: int):

    if value is None or isinstance(value, (bool, int, float, str)):
        return {'name': name, 'kind': 'value', 'value': value}

    if isinstance(value, bytes):
        return {'name': name, 'kind': 'value', 'value': value.hex()}

    if capture_groups_for(type(value)) is not None:
        value_id = id(value)
        if value_id not in seen_ids:
            seen_ids.add(value_id)
            to_visit.append(value)

        return {'name': name, 'kind': 'ref', 'ref': value_id}

    if depth >= _MAX_CONTAINER_DEPTH:
        return None

    rendered = iter_render_children(value)
    if rendered is None:
        return None

    render_kind, payload = rendered
    if render_kind == 'value':
        return {'name': name, 'kind': 'value', 'value': payload}

    return _classify_children(name, type(value).__name__,
                              payload, to_visit, seen_ids, depth)


@_check_types.do
def _classify_children(
    name: str,
    container_type: str,
    pairs,
    to_visit: deque,
    seen_ids: set[int],
    depth: int,
) -> dict:

    items = []
    item_count = 0
    truncated = False
    for child_name, child_value in pairs:
        if item_count >= _MAX_CONTAINER_ITEMS:
            truncated = True
            break

        item_entry = _classify_value(child_name, child_value, to_visit, seen_ids, depth + 1)
        item_count += 1
        if item_entry is not None:
            items.append(item_entry)

    if truncated:
        items.append({'name': '...', 'kind': 'value',
                      'value': f'(truncated after {_MAX_CONTAINER_ITEMS} items)'})

    return {'name': name, 'kind': 'container',
            'container_type': container_type, 'items': items}
