## FILES

#### __init__.py

`RotationRing` — assembles one axis's `TorusRing` + `InnerRing` + `OuterRing` into a single unit and owns the show/hide/pickability state machine between them. Initial state: only the torus ring is visible/pickable; `try_activate()` shows the protractor (inner+outer) and dims/depickables the torus; `set_dimmed()` dims a SIBLING axis's torus (called by whatever owns all three axis instances, since dimming a sibling is inherently a cross-axis decision this class can't make alone). This package holds the shared ring/protractor building blocks used by every view's rotation gizmo (`editor_3d`, `editor_pegboard`, `editor_schematic`) — the torus activation ring, the object-space and world-space protractor rings, the disc+tick+label geometry they both build on, and the per-tick pickable wrapper. It lives one level ABOVE `editor_3d`/`editor_pegboard`/`editor_schematic` (as `rotation_handlers.rotation_ring`, a sibling, not nested under any one view) specifically because it's shared across all three — the per-view `generic.py` modules each build `RotationRing` instances from here rather than each view having its own ring implementation.

#### _hit_test.py

`point_near_segment` — small screen-space hit-test helper shared by the ring/tick pick tests.

#### _protractor_base.py

`ProtractorRingBase`/`_Tick` — shared flat-washer + radial tick marks + numeric labels construction/rendering, used by both `inner_ring.py` and `outer_ring.py`. A short tick every degree, a longer labeled one every 10 degrees; each major tick's label is a camera-facing billboard (computed directly against `shapes.text`'s free `_billboard_matrices`, not through its `_CameraTrackingArena`, since a protractor label has no OBB/AABB-tracked owner). What differs between the two concrete rings (whether the angle tracks the object or stays fixed, and what a click/hover/drag does) is left entirely to the subclasses.

#### inner_ring.py

`InnerRing(ProtractorRingBase)` — the object-space protractor ring; its own-slot spin tracks the object's current Euler value for this axis directly, so its `0` tick always points at the object's own local zero. Grabbing anywhere along its band and dragging free-rotates the object about this axis — replacing the OLD fixed-handle drag in the retired `rotation_handlers/rotation_rings.py`'s `DragRotate`.

#### outer_ring.py

`OuterRing(ProtractorRingBase)` — the world-space protractor ring; its own-slot spin is held fixed regardless of drag (nests under the other two axes like every other ring — the "gyroscope" behavior — but this axis's own Euler value is zeroed before computing the plane, so its `0` tick never moves even while the inner ring/object spin past it). Owns hover-highlight/click-to-snap via a real ray-cast against each tick's own oriented box (`tick_pick_object.py`/`gl.object_picker`), not a hand-rolled screen-space nearest-point search. This each-axis-holds-its-own-Euler-slot-at-zero trick is easy to misread as a bug if you're not expecting the nested-Euler "gyroscope" convention — see `rotation_handlers/MAP.md`'s module-level description of the `Ry*Rx*Rz` ordering before changing anything here.

#### tick_pick_object.py

`TickPickObject(ObjectBase)` — a single outer-ring tick, wrapped just enough to be handed to `gl.object_picker.find_object`. Deliberately NOT a real scene object (`ObjectBase.__init__` never calls `mainframe.add_object`) — up to `TICK_COUNT` (360) of these can be alive per active axis, rendered explicitly by `ProtractorRingBase.render()`, never through the generic per-object path. It is still a genuine `ObjectBase` subclass (not a duck-typed lookalike) even though it never joins `add_object` — its `parent` type hint is enforced by `check_types.do` at runtime, so it has to really be one. Don't treat "never registered" as license to skip the real base class.

#### torus_ring.py

`TorusRing` — the always-visible, click-to-activate ring for one axis. Round-tube cross-section (unlike the flat disc rings) because a torus tube only stays circular under uniform scale, and this ring's diameter must match whatever object it's wrapped around — builds its own sized mesh rather than reusing the shared unit VBO the disc-based rings use. Clicking anywhere on the band activates that axis's protractor.
