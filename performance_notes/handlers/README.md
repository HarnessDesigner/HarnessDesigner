# performance_notes/handlers

Notes for `harness_designer/handlers/`. Every module now has a note. Rewritten 2026-11-13.

## Highest-cost items
- `rope_pull_handler.md` - the peg-board drag solver runs up to 18 `_evaluate_points` passes per mouse move whenever a move does not fit, and repeats structural lookups (`OR` selects that scan whole tables) on each pass. A warm start from the previous move's fraction and a per-drag cache of the structure lookups are the two changes with the largest effect.
- `wire_slack_handler.md` - the per-wire reconcile that the pegboard drags trigger (new note).
- `wire_routing_drag.md`, `wire_drag_base.md`, `wire_snap.md` - the wire drag planning and snap probes, per mouse move.
- Any `select(..., OR=True)` in a handler is a scan of the whole project table (`database/README.md` finding 2); the ones here run inside drag frames.

## Memory versus speed
Almost everything proposed here is a per-drag cache (a dict or a few floats) that lives only while the drag runs, so the memory cost is negligible; the notes say so where a change would hold more.
