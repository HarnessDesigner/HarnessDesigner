# harness_designer/ui/object_browser/objectbrowser.py

## Reverse-lookup helpers - full-project scans once per wire, per lookup
A wire's tree entry needs the bundles, splices, and transitions that contain it. The helpers find these by scanning the parent side of each relationship, because the wire has no foreign key back to its parents:

- `_bundles_containing_wire` loops over every bundle in the project and reads each bundle's `wires` (one query per bundle, through `pjt_wire_paths_table`).
- `_splices_containing_wire` loops over every splice and reads each splice's `wires`.
- `_transitions_for_wire` calls `_bundles_containing_wire`, then `_transitions_for_bundle` for each bundle found. `_transitions_for_bundle` loops over every transition and reads its six branch properties.

The comment in the code says these run only while the tree is built, so the cost is one-time per tree build. The cost is still roughly `W x (B + S + T)` database reads for W wires, B bundles, S splices, and T transitions, and it grows as the project grows. Each read is a round trip when the database is on a network, which the project's performance priorities call out.

Candidate fixes, to be measured before adopting:
- Build the parent-to-children map once per tree build (one pass over bundles, splices, and transitions), then look each wire up in that map. That makes the build linear in the number of rows read.
- Cache each bundle's wire-id set for the duration of the build, so the per-wire loop stops re-reading `wires`.

## `_resolve_object` - now a type check, not a probe
Before this pass, `_resolve_object` probed the value with `getattr(obj, 'get_object', None)`. It now checks `isinstance(obj, ObjectBase)` and calls `get_object()` on anything else. No new reads are added. The `None` case, which happens when a weakref has died, returns early as before.

## Search and selection
`_walk` and `_find_name_matches` walk the tree on each search, which runs on button press or return key, not on each keystroke. The selection timers defer cross-editor selection until the double-click window has passed, so a double click does not trigger the work twice. Neither needs a change.
