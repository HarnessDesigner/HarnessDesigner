# performance_notes/ui/object_browser

Covers `harness_designer/ui/object_browser/`.

- [objectbrowser.md](objectbrowser.md) - reverse-lookup scans per wire while the tree builds (the main concern in this folder)

## Reviewed for performance
`objectbrowser.py` (about 2,170 lines) was read for its tree-building and selection paths. The search walk (`_walk`, `_find_name_matches`) and the selection timers were checked for structure only.

## Functional notes (flagged, not fixed)
- `_resolve_object` previously probed for `get_object` with `getattr` and returned the value unchanged when the attribute was missing. It now checks `isinstance(obj, ObjectBase)` and calls `obj.get_object()` for everything else. Every value that reaches it is a project row (a `PJTEntryBase`) or an `ObjectBase`, so the behaviour is the same. If a non-project value ever gets into a tree item's weakref, it will now raise `AttributeError` instead of being returned unchanged.
