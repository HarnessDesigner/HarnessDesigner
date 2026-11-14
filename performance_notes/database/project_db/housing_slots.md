# harness_designer/database/project_db/housing_slots.py

How it all works: the module docstring of `database/project_db/pjt_housing.py` ("POOLED 3D STORAGE"); this note is only the cost.

Pooled 3D storage and the vector move / rotate of a housing (built 2026-11-14; design in the module docstring and `geometry/slot_pool.py`). Measured with the real `Point` / `Angle` classes and a stand-in database, interpreted, one frame of a housing with 100 cavities, 100 terminals, 100 seals and 6 accessories:

| Frame | Old cascade | Now |
|---|---|---|
| Rotate | 712 ms | 4.7 ms (152x) |
| Move | 4.7 ms | 0.93 ms (5x) |

The old rotate frame was 91% the three `Angle` setters per object rebuilding the quaternion and matrix (`geometry/angle/angle.md`); the old numbers also leave out the per-frame SQL for clone points (4-19 ms, see below) and the listeners that rebuild wires and objects. Results match the old cascade on 30 random housings x 6 gestures (1,431 point pairs including clone points, 2,180 angle rows): worst difference 1.8e-4 mm and 6e-5, and the pool and the database cache agree exactly on every pooled row.

## What a frame still costs (static read, not separately measured)
- `_write_points` visits every bound point slot and calls `batch_update` with one tuple per row (700 rows for a 100-cavity housing, about 1-2 ms), and `_rotate_angles` formats two strings per angle row (300 rows, about 2 ms) for the database cache. Both could be written once at the end of the gesture instead of every frame (the values are in the pool), which needs a lazy-value hook in `TableData`. They are the largest remaining part of a frame after the callbacks.
- One callback per pooled `Point` that has an object (700 of them measured 4.1 ms with only the cache listener bound). The listeners that rebuild wires and 3D objects are extra and were not measured; they are the next floor (a batched "these rows changed" notification would remove the per-point loop).
- The plan (part geometry per cavity, clone point ids) is built once per gesture: a few hundred property reads, a few milliseconds on the first frame.
- Clone points (`parent_point_id` children) are still found with one raw SQL query, but now once per plan instead of every frame. It scans the whole `pjt_points3d` table (no index on `parent_point_id`), 15-19 ms at 50,000 points, so the first frame of a drag on a large project still pays it (`pjt_housing.md`, finding on the cache lookup).

## Memory
Per housing: two Python lists of one reference per slot (`_point_rows`, `_angle_owners`), about 8 bytes per slot, a few KB. The registry `SlotPools3D._point_slots` holds one dict entry and a 4-tuple per bound point row, roughly 200 bytes each by estimate (not measured), so 60,000 pooled points are about 12 MB. The pool itself is in `geometry/slot_pool.md`.

## Waste to remove
`Angle3DMixin.angle3d` still reads two columns and `eval`s them (10 us each) before it asks the pool for the view, so for pooled classes the result is discarded; reordering it saves about 25 us per wrapper, once. `SlotPools3D.table` builds an eight-entry dict on every call (a few microseconds per table written per frame). The matrices of seeded angles are computed in one array call, but each `Angle` built over views still renormalises its quaternion in `Decimal` once (about 150 us per angle, at creation).
