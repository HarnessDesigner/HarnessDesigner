## FILES

#### __init__.py

Package init.

#### callback_mixin.py

`CallbackMixin` — provides `bind()`/`unbind()` and a `with:`-batching context manager for change notification. Mixed into `geometry/point.py`'s `Point`, `geometry/angle/angle.py`'s `Angle`, and `color.py`'s `Color`. Backing state uses the dunder-both-sides naming convention (`__callbacks__`/`__unbound_callbacks__`/`__ref_count__`) — see the root `MAP.md` / MEMORY.md's "Naming convention: dunders" entry for what that convention signals.

This is not "one pattern among several" — it is the architectural backbone of the entire program, and the user has said so directly and emphatically: "the whole callback system I designed for the angles and the points was a genius way to go about it. it is literally the backbone to this entire program." (2026-08-17) Instances of the classes mixing this in are cached by `db_id` — every lookup for the same id returns the *same object*, so **holding a reference to one of these IS the subscription**. `bind(callback)`/`unbind(callback)` notify on any change; this is how state propagates across UI controls, scene objects, and gizmos with **no event/signal library involved at all**. Confirmed real-world reach of this one mechanism, unmodified, in a single session: camera dirty-gating, the 3D headlight's direction tracking, the rotation-rings gizmo following a selected object's angle/scale/position, the 2D camera's position mirroring on every pan, and a planned (not-yet-built) protractor feature's camera-facing labels — all materially different problems, solved by another `bind()` call rather than inventing anything new. Default assumption for any new "recompute X whenever Y changes" feature: this is the mechanism, not a bespoke observer, a polling flag, or manual "call this after that" wiring — treat inventing a parallel update mechanism as a sign you've missed how this one already covers the case. Writers that are also bound listeners must use the unbind → write → rebind idiom to avoid feedback loops — see `ui/prop_ctrls/` and `gl/canvas_3d/rotation_rings.py`'s `Rings3D.apply_drag_angle` for the reference pattern.
