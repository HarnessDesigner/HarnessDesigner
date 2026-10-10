# harness_designer/handlers/wire_snap.py

## Line 58-95 (`SnapOverlay`) — one label, moved and shown on each hover
`show_message` sets the style sheet, sets the text, calls `adjustSize`, moves the label and shows it, all on every hover update while a snap target is active. Style-sheet changes and `adjustSize` are the costliest calls here; they can be skipped when the message and blocking state are unchanged.

## Line 99-130 (`_awg_fits`) and 131-165 (`capacity_warning`) — attribute reads per attached wire
`capacity_warning` reads `w.db_obj.part` up to three times for each attached wire inside a generator (line 155-157). Each `db_obj.part` read is a property access, which can be a database lookup (see `handler_base.md` for the same pattern on accessories). Reading the part once per wire into a local would cut the reads to one.

## Line 168-239 (`check_terminal_compat`, `check_splice_compat`) — runs on every hover over a candidate
These are called while the user hovers over a candidate terminal or splice during a snap session, so they run on mouse moves. Each call reads `terminal.wires` (or the splice siblings and branch wires) and their parts. The `capacity_warning` path reads every attached wire's part again. The results depend only on the target and the wire being placed, so they could be cached for the duration of one hover target.

## Line 240-297 (`resolve_picked`, `get_snap_info`) — cheap isinstance checks
Constant-time checks on the picked object. Fine.

## Line 301-325 (`snap_point`) — one attribute read
Returns a live `Point` for the target. Fine.

## Line 330-end (`commit_snap`) — database writes on mouse release
Writes the real connection for the snapped target once. Runs once per drop. Fine.
