# harness_designer/objects/terminal.py

## Line 329-424 (`_junction_push_length`) — scans every cavity in the housing to find one immediate neighbour
Every time a terminal gains its second wire (`_make_room_for_second_wire`,
which calls this), the loop at line 384 (`for other_cavity in
housing.cavities`) walks *every* cavity in the housing, doing a
`housing.cavity_geometry.get(other_cavity.db_id)` dict lookup and a
row-pitch distance check (line 394) for each one, just to find the (at
most two) cavities immediately above/below this one in the stack. For a
large connector housing (hundreds of cavities) this is O(cavities) per
terminal that becomes a junction, rather than O(1)/O(log n) if
`cavity_geometry`'s stack order were looked up directly (e.g. an index by
row position, or walking the two neighbouring `idx` slots directly instead
of scanning the whole housing). Not a hot per-frame path -- it only runs on
the interactive moment a terminal's wire count goes from one to two -- but
worth a second look if adding a wire to a densely-populated housing is ever
reported as sluggish.

## Line 72-83 (`wires` property) — prunes dead weakrefs on every access, not just periodically
Every read of `self.wires` walks the full `_wire_refs` list, dereferences
every weakref, and rebuilds `self._wire_refs` from the survivors (line 82)
-- so a terminal with N attached wires pays an O(N) weakref-dereference
pass on every single access, including the `existing_wires = self.wires`
call inside `add_wire` (line 140), which is itself in the per-wire-attach
path. For a terminal's typical wire count (rarely more than a handful)
this is negligible, but the pattern -- pruning on read rather than lazily
(e.g. only when a weakref actually resolves to `None`) or via a
`weakref.WeakSet`-style container that prunes itself -- is repeated
identically in `splice.py` (`branch_wires`) and `wire_service_loop.py`,
so if any of these three ever needs to scale past "a handful," the fix is
the same in all three places.
