# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The housing row object, and the documentation of POOLED 3D STORAGE (and, in section 15, of the same
for the peg board and the schematic).

This file is where the whole pooled-storage design is written down. The other files that take
part (listed in section 2) keep only a description of their own part and point here. When
the design changes, change this text in the same edit.

Contents
    1. What it is and why
    2. The files and what each one owns
    3. The storage: pools, chunks and blocks
    4. A housing's slots (the layout)
    5. When slots are allocated and released
    6. Binding: which row lives in which slot
    7. How a Point or an Angle gets its view
    8. The rules that keep it correct
    9. The move and the rotate, step by step
   10. What is different from the old per-object cascade
   11. Changing it (a new object type, a new layout, another view)
   12. Errors you can get and what they mean
   13. What was checked, and what was not
   14. Limitations and open work
   15. The peg board and the schematic


1. WHAT IT IS AND WHY
---------------------
Moving or rotating a housing has to change every point and every angle of the housing, its
cavities, terminals, seals and accessories, on every mouse move. Doing that one Python object
at a time (a ``Point`` per point, an ``Angle`` per angle, each going through ``Decimal``
arithmetic and setters that rebuild a quaternion and a matrix) cost 712 ms per rotate frame
for a housing with 100 cavities, each with a terminal and a seal (measured, interpreted).

The data of all of those objects now lives in a few contiguous float32 NumPy arrays (the
"pools"), laid out so that one housing is one slice. ``Point``, ``Quaternion`` and ``Angle``
objects do not own their numbers any more: they hold VIEWS of their row of a pool. A move or
a rotate is a few array operations over the housing's slice, and then one callback per
``Point`` that has an object. The same frame takes 4.7 ms (a move frame went from 4.7 ms to
0.9 ms), and gives the same results as the old cascade (section 13).

The design is the user's. The decisions that shape everything else:
    * Slots are allocated for a housing as soon as the housing's row object is known, whether
      the slots will be used or not (pre-allocation), in fixed-size chunks that never grow,
      move or compact.
    * Points, and angles, are in separate pools. The euler angles, quaternions and matrices
      of the angles are three arrays that share one slot index.
    * ``Point`` and ``Angle`` never learn a slot number; they hold the view they were built
      with. Only the housing's slots object and the pool know slot numbers.
    * The housing's database row object hands out the views (through the pools it owns), so
      references pass back from it to the objects that need them.


2. THE FILES AND WHAT EACH ONE OWNS
-----------------------------------
geometry/slot_pool.py
    ``SlotPool`` (chunks, best-fit blocks, release), ``SlotBlock``, ``SlotField`` and
    ``PoolMember``, the base class of ``Point`` and ``Angle``. Knows nothing about housings.
geometry/batch.py
    The array math: ``compose``, ``to_matrices``, ``euler_from_matrices``,
    ``rotate_points``. Knows nothing about pools or housings.
geometry/point.py, geometry/angle/angle.py
    ``Point(..., data=view)`` and ``Angle.from_views(...)`` build objects over pool rows.
    ``_leave_pool()`` gives an object a private copy of its data.
database/project_db/housing_slots.py
    ``SlotPools3D`` (the two pools of a project, every housing's slots, the row -> slot
    registry, ``build_point`` / ``build_angle``) and ``HousingSlots3D`` (one housing's blocks,
    its bindings, its plan, ``move`` and ``rotate``).
database/project_db/pjt_housing.py (this file)
    ``PJTHousing.__init__`` takes the slots, ``delete`` releases them, ``insert`` and
    ``update_cavities`` call ``cavities_created``, ``PJTHousingsTable.update`` rebinds a slot
    when an accessory's point column is written, ``_update_position3d`` / ``_update_angle3d``
    compute the delta and hand it to ``move`` / ``rotate``, ``find_child_point_ids`` finds the
    clone points.
database/project_db/pjt_cavity.py, pjt_terminal.py, pjt_seal.py
    Their tables' ``update`` (and the terminal's and the seal's ``insert``) rebind a slot when
    a point column is written; ``PJTCavity.angle3d`` is a view of the angle pool.
database/project_db/pjt_point3d.py
    ``PJTPoint3D.point`` asks the pools for its view; ``delete`` unbinds the row.
database/project_db/mixins/angle3d.py
    ``Angle3DMixin.angle3d`` asks the pools for the view (housing, accessories, terminals,
    seals).
database/project_db/pjt_bases.py
    ``PJTTables.slot_pools3d`` (created in ``__init__``, reset and filled in ``load``) and
    ``PJTTables.gesture_serial``.


3. THE STORAGE: POOLS, CHUNKS AND BLOCKS
----------------------------------------
There are two pools per view; this is the 3D view's pair (``SlotPools3D``).

    point pool    ``data``    (n, 3)      float32      neutral value: 0, 0, 0
    angle pool    ``quat``    (n, 4)      float32      neutral value: 1, 0, 0, 0 (identity)
                  ``euler``   (n, 3)      float32      neutral value: 0, 0, 0
                  ``matrix``  (n, 3, 3)   float32      neutral value: identity

float32 is what ``Point`` / ``Quaternion`` / ``Angle`` always stored; every row of a pool is
a C-contiguous array, which is what the code that aliases a ``Point``'s array expects.

A pool is a list of chunks. A chunk is a set of arrays of the pool's fixed length, allocated
once at full size. A normal chunk holds 10 housings of 100 cavities each:

    point chunk   10 * (7 + 7 * 100)  = 7,070 slots * 12 bytes =  85 KB
    angle chunk   10 * (7 + 3 * 100)  = 3,070 slots * 64 bytes = 196 KB

so a housing with 130 cavities still fits in one chunk, and a typical 10-cavity housing
(77 point slots, 37 angle slots) is a few KB, about 90 of them to a chunk.

A BLOCK is a contiguous run of slots inside one chunk, handed out by ``SlotPool.allocate``:
    * Best fit: the smallest free run that is big enough, searched over every chunk. A chunk's
      unused tail is just another free run. When nothing fits, a new chunk is created (large
      enough for the request if the request is bigger than a normal chunk).
    * ``SlotPool.release`` returns a block: every live object built over it first takes a
      private copy of its data (so it can never write into the next owner's rows), the rows
      are reset to the neutral value, and the free run is merged with its free neighbours.
      Merging is bookkeeping; nothing is ever moved or compacted.
    * ``SlotPool.array(block, name)`` is a zero-copy slice of the whole block;
      ``SlotPool.row(block, name, offset)`` is the view of one slot, which is what a ``Point``
      or ``Angle`` is built over. ``register`` / ``members`` / ``evict`` keep a weak reference
      to the object built over each slot.
    * ``SlotPool.reset()`` drops every chunk (a project is being replaced). Storage is dropped,
      not wiped: an object that still holds a view keeps its own array alive and cannot write
      into a new project's rows.

Why nothing moves: ``Point._data`` is aliased by other code (the culling pipeline keeps the
array; ``Point.attach`` copies into it in place). The array behind a live object must never
be replaced, so a slot's address is fixed for as long as the block lives.


4. A HOUSING'S SLOTS (THE LAYOUT)
---------------------------------
Each housing has two blocks in each pool: a FIXED block, and, once it has cavities, a CAVITY
block (a second block so that cavities created late, when the housing's catalog part had none
yet, can get theirs later). In this text a slot number is the "global" number inside the
housing: fixed block 0-6, then the cavity block.

    FIXED BLOCK (7 slots; the points and the angles use the same order)
        0 housing   1 boot   2 cover   3 cpa lock   4 housing seal   5 tpa lock 1   6 tpa lock 2

    CAVITY BLOCK, per cavity i (i = the cavity's place in the housing's cavity rows when the
    block was allocated)
        POINTS, 7 per cavity, global slot  7 + i * 7 + role
            0 cavity                          cavities.point3d_id
            1 cavity wire point               cavities.wire_point3d_id
            2 terminal                        terminals.point3d_id, the SAME row as
                                              cavities.terminal_point3d_id
            3 terminal wire point             terminals.wire_point3d_id
            4 terminal attach point           terminals.attach_point3d_id (a wire's start /
                                              stop point when it is seated)
            5 seal                            the point of the seal in this cavity: the
                                              terminal's seal, or a plug / dummy pin when the
                                              cavity has no terminal (a cavity has one or the
                                              other, never both)
            6 terminal seal position          terminals.seal_point3d_id, the SAME row as the
                                              point3d_id of the seal that sits on the terminal
                                              (so that seal's slot 5 is an alias of slot 6)
        ANGLES, 3 per cavity, global slot  7 + i * 3 + role
            0 cavity   1 terminal   2 seal (the terminal's seal, or the cavity's own)

Rows behind the fixed block:
    points   the housing's own columns point3d_id, boot_point3d_id, cover_point3d_id,
             cpa_lock_point3d_id, seal_point3d_id, tpa_lock_1_point3d_id,
             tpa_lock_2_point3d_id. An accessory row is created with the housing's column as
             its own point3d_id, so the housing and its accessory share ONE point row and one
             slot.
    angles   the housing row, and the accessory rows found by ``housing_id`` (the tpa locks by
             ``idx`` 1 and 2; the housing's seal is the seals row with a ``housing_id``).

Example, a housing with 10 cavities: 7 + 10 * 7 = 77 point slots and 7 + 10 * 3 = 37 angle
slots.

SHARED POINT ROWS ARE ALLOCATED ONCE. These columns hold the same row, and the DB classes make them so:

    pjt_housings.boot_point3d_id        = pjt_boots.point3d_id
    pjt_housings.cover_point3d_id       = pjt_covers.point3d_id
    pjt_housings.cpa_lock_point3d_id    = pjt_cpa_locks.point3d_id
    pjt_housings.seal_point3d_id        = pjt_seals.point3d_id      (the housing's own seal)
    pjt_housings.tpa_lock_1_point3d_id  = pjt_tpa_locks.point3d_id  (idx 1)
    pjt_housings.tpa_lock_2_point3d_id  = pjt_tpa_locks.point3d_id  (idx 2)
    pjt_cavities.terminal_point3d_id    = pjt_terminals.point3d_id
    pjt_terminals.seal_point3d_id       = pjt_seals.point3d_id      (a seal on the terminal)

``PJTCavity.terminal_position3d_id`` returns the seated terminal's row instead of making a second one;
``PJTTerminalsTable.insert`` writes its point into the cavity's column (and drops the cavity's earlier
guess); ``PJTSealsTable.insert`` uses the terminal's seal point. ``HousingSlots3D.bind_point`` is the
backstop: a row that is asked for by a second slot is NOT given a second slot. The first slot owns it,
the second is an ALIAS and stays empty (a move or a rotate of a block needs the row once), and when the
owner lets go of the row (a column rewritten, the point deleted, the housing released) the first alias
takes it over.

Seals are of three kinds: the housing's own (fixed block), a seal on a terminal (``terminal_id``
set) and a plug or dummy pin (``cavity_id`` set). The last two use their cavity's seal slots.


5. WHEN SLOTS ARE ALLOCATED AND RELEASED
----------------------------------------
Allocation is by "get or create" on the pools (``SlotPools3D.housing(housing_id)``), which
keeps the housing's ``HousingSlots3D`` in a dict by row id. The pools, not the row object, own
the slots, so a row object that is dropped and built again finds the same slots.

    Project load       ``PJTTables.load``: ``mainframe.unload()``, ``slot_pools3d.reset()``,
                       the tables are built and their caches loaded, then
                       ``slot_pools3d.allocate_all()`` allocates every housing of the project
                       (fixed block, cavity block, every existing row bound and seeded). This
                       runs before anything builds a ``Point`` or an ``Angle``.
    Housing added      ``PJTHousingsTable.insert`` inserts the housing row and builds the
                       ``PJTHousing`` (``__init__`` -> ``housing(db_id)``: the fixed block;
                       there are no cavity rows yet). Right after the cavity rows are
                       inserted it calls ``cavities_created()``: the cavity block. The
                       accessory points are created on demand by the housing's getters.
    Cavities late      ``PJTHousing.update_cavities`` inserts the cavity rows and calls
                       ``cavities_created()`` BEFORE it builds the cavity row objects and
                       facades (which build ``Point`` objects).
    Housing deleted    ``PJTHousing.delete`` deletes its accessories and cavities, then the row,
                       then ``slot_pools3d.release(db_id)``: both blocks go back to their pools.
    Project replaced   ``slot_pools3d.reset()`` at the start of the next ``load``.

``cavities_created()`` may be called once per housing; a second call raises.


6. BINDING: WHICH ROW LIVES IN WHICH SLOT
-----------------------------------------
A slot is BOUND to a row when the row's data is put into it. ``HousingSlots3D`` keeps, per
housing, ``_point_rows`` (the point row id in each point slot) and ``_angle_owners`` (the
(table name, row id) of the owner in each angle slot); ``SlotPools3D`` keeps a registry
``_point_slots`` (point row id -> housing slots, slot, block, offset).

Binding a point (``bind_point``) seeds the slot from the row's x, y, z in the database cache,
registers the row, and removes whatever row was bound before (its ``Point``, if it has one,
leaves the pool). Binding an angle (``bind_angle``) seeds quaternion and euler from the row's
``quat3d`` / ``angle3d`` strings and the matrix from the quaternion; a changed owner evicts the
previous owner's ``Angle``. Binding ``None`` clears the slot to its neutral value.

What causes a binding:
    Allocation                  every row that exists then (housing, accessories, cavities,
                                their terminals and seals).
    A point-id column written   ``PJTHousingsTable.update``, ``PJTCavitiesTable.update`` and
                                ``PJTTerminalsTable.update`` look at the columns they are given
                                (the lists ``HOUSING_POINT_COLUMNS``, ``CAVITY_POINT_COLUMNS``,
                                ``TERMINAL_POINT_COLUMNS`` in housing_slots.py) and call
                                ``SlotPools3D.column_changed``. Every getter and setter that
                                creates or changes one of these ids ends in ``update``, so they
                                are all covered. ``PJTTerminalsTable.insert`` binds the new
                                terminal's point the same way.
    A seal row                  ``PJTSealsTable.insert`` / ``update`` call ``seal_changed``,
                                which binds the point of a seal on a terminal or in a cavity.
                                A housing's own seal uses the housing column.
    A point row deleted         ``PJTPoint3D.delete`` calls ``point_deleted``, which clears the
                                slot, so nothing writes to a deleted row.
    An angle owner              resolved by pull (section 7) and re-checked when a plan is
                                built (section 9): a terminal or seal that appeared, vanished or
                                was replaced is noticed there.

A terminal's point is bound from two places (the cavity's ``terminal_point3d_id`` and the
terminal's ``point3d_id``); they are the same row. If they differ, the terminal's wins.


7. HOW A POINT OR AN ANGLE GETS ITS VIEW
----------------------------------------
Points.   ``PJTPoint3D.point`` (the only place a ``Point`` is built for a ``pjt_points3d``
          row) calls ``SlotPools3D.build_point(row_id, point_db_id)``. If the row is bound,
          the ``Point`` is built over the slot's view (``Point(..., data=view)``) and
          registered with the pool; otherwise ``None`` comes back and a normal ``Point`` is
          built (wire waypoints and every other point are not in a housing's group). This works
          whoever asks first: the housing, a cavity, a terminal or a wire, because the row ->
          slot registry does not depend on the asker.
Angles.   ``Angle3DMixin.angle3d`` (the housing, its accessories, terminals, seals) and
          ``PJTCavity.angle3d`` call ``SlotPools3D.build_angle(table_name, row_id, db_id)``
          once per row object (the result is cached in ``_stored_angle3d``). The pools find the
          housing and the slot from the table name and the row (cavity -> its housing;
          terminal -> its cavity -> housing; seal -> housing, terminal or cavity; accessory ->
          its ``housing_id``), bind the owner, and build ``Angle.from_views`` over the slot's
          quaternion, euler and matrix rows. A table that is not in a group (a note) gets
          ``None`` and a normal ``Angle``.

A ``Point`` that already exists when its row is bound (``bind_point``) or asked for (``build_point``)
is not rebuilt and not refused: ``housing_slots._seat_point`` calls ``Point._join_pool`` so its own array
is copied into the slot and the slot becomes its array. Allocating before anything builds a ``Point``
(section 5) is still the normal order, but nothing breaks when it is not the order.


8. THE RULES THAT KEEP IT CORRECT
---------------------------------
    1. The pool is the live data. For every bound slot the database cache is brought up to
       date after each move or rotate (not only for slots that have an object), so the cache
       and the pool agree whenever no cascade is running. A slot is seeded from the cache only
       when a row is bound to it.
    2. An object over a pool row keeps the same array for as long as it is bound, until
       ``_leave_pool`` (release, eviction) gives it a private copy. The one other change of array
       is ``Point._join_pool``: a ``Point`` that existed BEFORE its row got a slot (a wire end
       dropped on a cavity or a terminal) has its own array copied INTO the slot and the slot
       becomes its array (never the other way round: the live Point is the truth, the cached row
       may be stale). Whoever kept the old array through ``as_numpy`` keeps a stale copy.
    3. A point row is bound to at most one slot, and a slot holds at most one row. A row asked
       for twice is allocated once (see the end of section 4).
    4. Point-id columns of a housing, a cavity and a terminal are written only through their
       table's ``update`` (and the inserts named in section 6); that is what keeps the
       bindings current.
    5. Unused slots hold neutral values, so a whole block can be rotated with no masks.
       Slots whose owner is absent are rotated too (section 10).
    6. A plan (section 9) is valid for one gesture only.
    7. Angle objects fire no callbacks during a cascade (as before); only ``Point`` objects
       do, one callback each. The values of every slot, points and angles, are final before
       the first callback fires.


9. THE MOVE AND THE ROTATE, STEP BY STEP
----------------------------------------
Callers.   Dragging or rotating a housing writes its own ``Point`` or ``Angle``, which fires the
callback bound to ``PJTHousing._update_position3d`` / ``_update_angle3d``. The drag handlers
open a gesture first (``PJTTables.begin_gesture``); typing a value in the property grid does
not.

``PJTTables.gesture_serial`` counts opened gestures (it is incremented when the depth goes from
0 to 1). ``HousingSlots3D`` keeps one PLAN and reuses it while ``gesture_depth > 0`` and the
serial has not changed; outside a gesture every call builds its own plan.

THE PLAN (``HousingSlots3D._build_plan``), built on the first frame of a gesture:
    * walks the housing's cavities, terminals and seals and re-checks who owns each angle slot
      (``bind_angle``): a terminal or seal that is new, gone or replaced is handled here;
    * per cavity: its part's OBB corners, the part model's own quaternion, and the corner
      indices of the forward face (face 4) and the up face (face 3);
    * per accessory (tpa lock 1, housing seal, tpa lock 2, boot, cpa lock, cover): a mode, and
      for the OBB mode the model's OBB, quaternion and the corner indices of its own forward and
      up faces. Mode OBB: the part has a model with usable ``forward_up`` faces. Mode MATRIX: no
      part or no model, so the plain rotation is used. Mode SKIP: the faces are -1 (the
      accessory's angle is left alone);
    * the row ids of the clone points of the housing's wire-side points
      (``find_child_point_ids``: one SQL query for the whole set). The clone ``Point`` objects
      are built the first time they are needed and kept with the plan.

MOVE (``HousingSlots3D.move``, called by ``_update_position3d`` with the delta of the housing's
point; the housing's own point, fixed slot 0, is not moved):
    1. get the plan;
    2. add the delta to the fixed block (slots 1-6) and to the whole cavity block (float32);
    3. ``_write_points``: write x, y, z of every bound point slot (including slot 0) into the
       database cache with one ``batch_update``; inside a gesture that only records the change;
    4. move the clone points (set x, y, z, fire their callbacks);
    5. fire the callbacks of the pooled points that have an object (order below).

ROTATE (``HousingSlots3D.rotate``, called by ``_update_angle3d`` with the rotation delta
``angle._q - o_angle._q`` as a quaternion and the housing's position as the center; the
housing's own angle, fixed slot 0, is the input and is not recomputed):
    1. get the plan;
    2. rotate every point slot of both blocks about the center (``batch.rotate_points``);
    3. ``_write_points`` as above;
    4. rotate the clone points about the center and fire their callbacks;
    5. angles (``_rotate_angles``, ``_angles_from_obb``), for the cavities and then the accessories:
         new quaternion       q = compose(current quaternion, delta). ``compose(a, b)`` is
                              ``Quaternion.__add__``: ``b (x) a`` normalised, ``b`` applied in
                              world space before ``a``'s own rotation.
         OBB orientation      q_obb = compose(model quaternion, q); rotate the part's OBB corners
                              by q_obb; the forward direction is the centroid of the four
                              forward-face corners minus the centroid of all eight (likewise up);
                              right = up x forward; up = forward x right; the matrix has columns
                              right, up, forward.
         Euler angles         from that matrix (YXZ: pitch, yaw, roll in degrees), each wrapped
                              to within 180 degrees of the previous value so the displayed
                              numbers never jump.
         Rows left alone      (cavity without a known part; accessory in mode SKIP; a face whose
                              direction cannot be read) keep their slot as it was and are not
                              written to the cache.
         MATRIX rows          (an accessory without a model; a degenerate "right" vector) use
                              the plain rotation matrix of q instead of the OBB matrix.
       The quaternion, euler and matrix of a cavity are written to the cavity's slots AND to the
       slots of its terminal and its seal (they take their cavity's orientation); the accessories
       get their own results. Then, for every updated slot that has an owner bound, the strings
       ``quat3d`` / ``angle3d`` are written into that owner's row, with one ``batch_update`` per
       table (the slots of an absent terminal or seal are written but have no row to update);
    6. fire the callbacks of the pooled points that have an object, in this order: the cavity
       points; the accessory points (cover, housing seal, boot, tpa lock 1, tpa lock 2, cpa
       lock); the terminal points; then the terminal wire points, the terminal attach points,
       the cavity wire points, the seal points and the terminal seal-position points.
After the cascade ``_update_angle3d`` calls ``_populate('angle3d')``.

Outside a gesture the same steps run, and ``batch_update`` writes to the database immediately
(one ``executemany`` and commit per table) instead of recording a change.


10. WHAT IS DIFFERENT FROM THE OLD PER-OBJECT CASCADE
-----------------------------------------------------
    * A rotation moves EVERY point of the housing's slots, including points whose owner is
      absent: an empty cavity's wire point and terminal point, a terminal's seal-position
      point, a plug seal's point. The old cascade skipped everything of a cavity without a
      terminal except the cavity's own point (it did rotate that seal's angle). A move does the
      same.
    * The terminal seal-position point (``terminals.seal_point3d_id``) is carried along with its
      housing; before, it was never moved after it was first computed.
    * Every value is final before any callback fires. The old code set a point and fired its
      callbacks one point at a time and only then computed the angles.
    * The clone points' callbacks fire before the pooled points' callbacks (they used to fire
      last).
    * The clone points are looked up once per gesture, not on every frame.
    * Angle objects are views of slots; ``PJTCavity.angle3d`` is cached on the row object (it
      read and parsed the row on every access).
    * Results are computed in float64 and stored as float32 (the stored precision never
      changed); each quaternion product is normalised. They agree with the old results to
      1.8e-4 mm for points and 6e-5 for angles (section 13).
The peg board and the schematic cascades (``_update_position_pegboard``, ``_update_angle_pegboard``,
``_update_position2d``, ``_update_angle2d``) use the same mechanism now (section 15).


11. CHANGING IT
---------------
A new object type in the housing's group (a new accessory, say): add its slot constant and raise
``FIXED_COUNT``; add its point column to ``_HOUSING_POINT_COLUMNS`` and its table to
``_ACCESSORY_SLOTS``, ``SlotPools3D.table`` and ``_resolve_angle``; add it to
``_ACCESSORY_ORDER`` / ``_ACCESSORY_POINT_ORDER`` and to ``_build_plan``; check the chunk sizes
(``POINT_CHUNK_SLOTS``, ``ANGLE_CHUNK_SLOTS``); make its class get its ``Angle`` from
``Angle3DMixin`` so the pull in section 7 finds it.

A new slot per cavity: change ``POINTS_PER_CAVITY`` / ``ANGLES_PER_CAVITY`` and the role
constants, ``_bind_cavities``, the column lists and (for a point that has a row created on
demand) make sure the code that creates the row writes its id column through the table's
``update``. Stored data is not affected (slot numbers are never stored).

Another view: the peg board and the schematic are built (section 15): pools of their own and a
layout of their own, as subclasses of ``housing_slots_base.py``. A fourth view would be a third subclass.

Never: swap ``Point._data`` or an ``Angle``'s arrays for others; write a point-id column of a
housing, cavity or terminal without ``update``; build a ``Point`` of a pooled row before the
housing was allocated; keep a slot number in a ``Point`` or an ``Angle`` or in the database.


12. ERRORS YOU CAN GET AND WHAT THEY MEAN
-----------------------------------------
RuntimeError "a point row cannot be bound to two slots"
    ``SlotPools3D.remember_point`` was handed a row that already has another slot. ``bind_point``
    makes the second slot an alias first, so this can only come from code that skips ``bind_point``.
RuntimeError "this housing already has its cavity slots"
    ``cavities_created`` was called twice; cavity rows are created once per housing.
KeyError raised from ``cavity_slot``
    A cavity row exists that was not present when the cavity block was allocated (it was
    created without ``cavities_created``; the single-cavity ``PJTCavitiesTable.insert`` path
    does this and has no live callers).
IndexError while loading a project
    ``bind_point`` / ``bind_angle`` looked up a row that does not exist: a housing, cavity or
    terminal column points at a deleted row (dangling reference in the data).
ValueError from ``SlotPool``
    "block already released", "slot already has live member", or a block of fewer than one slot.


13. WHAT WAS CHECKED, AND WHAT WAS NOT
--------------------------------------
Checked with throwaway scripts (kept outside the repo; no test files are kept, by the project's
rule), interpreted Python, the real ``Point`` / ``Angle`` / ``Quaternion`` classes and the real
``slot_pool`` / ``batch`` / ``housing_slots`` / ``PJTHousing`` cascade methods, with stand-in
tables:
    * ``SlotPool``: 6,000 random allocations and releases against an independent model (no
      overlapping blocks, free runs always merged and sorted, capacity conserved, best fit
      confirmed by brute force, rows neutral where free, members told to leave on release).
    * ``batch``: against ``Quaternion.__add__``, ``Quaternion.as_matrix``,
      ``_euler_from_matrix_continuous`` and the old point rotation.
    * ``Point`` / ``Angle`` over views: aliasing in both directions, setters, ``attach``,
      singleton behaviour, release.
    * The cascades: the old methods (from git HEAD) and the new ones on two identical random
      worlds (cavities with and without terminals, terminal seals, plug seals, accessories in
      every mode, clone points), driven through 6 random moves and rotates each, 30 worlds: 1,431
      point pairs (966 of them clone points) and 2,180 angle rows agree to 1.8e-4 mm and 6e-5, and
      the pool and the database cache agree exactly on every pooled row.
    * Lifecycle: cavities created late, a ``Point`` built too early is refused, a column change
      rebinds, a deleted row unbinds, the plan is built once per gesture, release and reuse.
    * Timing (100 cavities, 100 terminals, 100 seals, 6 accessories): rotate frame 712 ms ->
      4.7 ms, move frame 4.7 ms -> 0.9 ms. The old figures leave out the per-frame SQL for
      clones and any listener bound to a point beyond the database cache.
NOT checked: the app itself, the real ``PJTTables.load``, ``PJTHousingsTable.insert``,
``update_cavities`` and table ``update`` hooks against a real database; any view other than 3D
(section 15 says what was checked for the peg board and the schematic); the listeners that rebuild wires and 3D objects when a point's callbacks fire (they are the next
cost, unmeasured).


14. LIMITATIONS AND OPEN WORK
-----------------------------
    * A terminal that is deleted keeps its slots bound until its point rows are deleted or the housing is.
    * A terminal moved to another cavity keeps its old slots for its points; a seal moved off a
      terminal or cavity keeps its slot bound.
    * The database cache is written for every bound point slot and the angle rows are formatted
      as strings on every frame. They could be written once, at the end of the gesture, from the
      pool (needs a lazy value in ``TableData``).
    * There is still one callback per pooled ``Point`` that has an object; a batched "these
      rows changed" notification would remove that loop.
    * The clone points are found with a raw SQL query that scans the point table (no index on
      ``parent_point_id``); it now runs once per plan, the first frame of a gesture.
    * ``Angle3DMixin.angle3d`` still reads and parses the row before it asks the pool.
    * A chunk that becomes completely empty is not freed.

15. THE PEG BOARD AND THE SCHEMATIC
----------------------------------
The peg board and the schematic had the problem the 3D view had (a housing move or rotate went through one
Python ``Point`` / ``Angle`` at a time) and have the same solution: pools of their own, one housing is a
few slices, a move or a rotate is a few array operations and then one callback per ``Point`` that has an
object. Everything of sections 3 to 8 holds for the two views (chunks, blocks, binding, aliases, the view a
``Point`` is built over, the rules). The 3D classes were left as they were; the two views are subclasses of
a shared base. The numbers of a move and a rotate are in the last part of this section.

Files
    database/project_db/housing_slots_base.py
        ``SlotsBase`` (one housing's point blocks, ``bind_point`` with its aliases, ``_write_points``,
        ``terminal_left`` / ``terminal_arrived``) and ``PoolsBase`` (the point pool, the row -> slot
        registry, ``build_point``, ``point_deleted``, ``terminal_moved``): the parts of sections 3, 6 and 7
        that do not depend on the view.
    database/project_db/housing_slots_pegboard.py
        ``HousingSlotsPegboard`` and ``SlotPoolsPegboard`` (the point pool AND the angle pool,
        ``build_angle``, ``seal_changed``): the layout, what is bound, the plan, ``move`` and ``rotate``.
    database/project_db/housing_slots_schematic.py
        ``HousingSlotsSchematic`` and ``SlotPoolsSchematic``: points only.
    database/project_db/pjt_housing.py (this file)
        ``PJTHousing.__init__`` takes ``_slots_pegboard`` and ``_slots_schematic``; ``delete`` releases
        them; ``insert`` and ``update_cavities`` call ``cavities_created`` on both;
        ``_update_position_pegboard`` / ``_update_angle_pegboard`` / ``_update_position2d`` /
        ``_update_angle2d`` work out the delta and hand it to ``move`` / ``rotate`` (what is not a cascade,
        the stored quaternion and Euler angles and ``_populate``, stayed); ``PJTHousingsTable.update`` rebinds
        a slot when a point column is written.
    pjt_cavity.py, pjt_terminal.py, pjt_seal.py
        Their tables' ``update`` (and the terminal's ``insert`` for the schematic, the seal's ``insert``)
        rebind slots; ``PJTTerminalsTable.update`` also calls ``terminal_moved`` when ``cavity_id`` is written.
    pjt_point_pegboard.py, pjt_point2d.py
        ``.point`` asks the pool for its view, ``delete`` unbinds the row.
    mixins/angle_pegboard.py
        ``angle_pegboard`` asks the pool for the view (the same fallback to a normal ``Angle`` as in 3D).
    pjt_bases.py
        ``PJTTables.slot_pools_pegboard`` and ``slot_pools_schematic``, created, reset and filled in ``load``
        beside ``slot_pools3d``.

THE PEG BOARD LAYOUT (``housing_slots_pegboard.py``)
    FIXED BLOCK, POINTS (3)   0 housing        pjt_housings.point_pegboard_id
                              1 housing seal   the housing seal row's own point_pegboard_id
                              2 housing seal position   pjt_housings.seal_point_pegboard_id
    FIXED BLOCK, ANGLES (2)   0 housing   1 housing seal
    CAVITY BLOCK, POINTS, 8 per cavity, global slot  3 + i * 8 + role
        0 cavity                   cavities.point_pegboard_id
        1 cavity wire point        cavities.wire_point_pegboard_id
        2 terminal                 terminals.point_pegboard_id
        3 terminal wire point      terminals.wire_point_pegboard_id
        4 terminal attach point    terminals.attach_point_pegboard_id
        5 seal                     the point_pegboard_id of the seal on the terminal, or of the plug / dummy
                                   pin when the cavity has no terminal
        6 terminal seal position   terminals.seal_point_pegboard_id
        7 cavity terminal point    cavities.terminal_point_pegboard_id
    CAVITY BLOCK, ANGLES, 3 per cavity, global slot  2 + i * 3 + role: 0 cavity, 1 terminal, 2 seal.

    Not as in 3D: there is no accessory but the housing seal on the peg board; the seal is TWO rows (the
    owner's ``seal_point_pegboard_id``, the root, and the seal's own ``point_pegboard_id``, which the add
    handlers attach to it with ``Point.attach``), both pooled; and a cavity's ``terminal_point_pegboard_id`` is
    a row of its own (it is the terminal's row in 3D), so it has its own slot (7). A row that two columns
    share is an alias as in section 4, whichever way the data came about.

THE SCHEMATIC LAYOUT (``housing_slots_schematic.py``)
    FIXED BLOCK, POINTS (1)   0 housing        pjt_housings.point2d_id
    CAVITY BLOCK, POINTS, 3 per cavity, global slot  1 + i * 3 + role
        0 cavity                   cavities.point2d_id (``terminal_position2d`` is the same row)
        1 terminal wire point      terminals.wire_point2d_id
        2 terminal                 terminals.point2d_id
    There is NO angle pool: a cavity and a terminal have no ``angle2d`` that follows the housing (their
    names stay upright, only their anchor points turn), so the housing's one ``Angle`` is a normal one and a
    pool of one angle per housing would batch nothing. A terminal whose own point was never made
    (``point2d_id`` NULL) has no slot bound, and is skipped as it always was.

THE MOVE AND THE ROTATE (peg board)
    Callers.  As in section 9. The plan holds who owns each angle slot (re-checked on the first frame of a
    gesture: ``bind_angle`` for each cavity's terminal and seal and for the housing seal) and the clone
    points (``parent_point_id``) of every bound point of the housing, found with one SQL query per 400 rows
    that are not themselves in a slot.
    MOVE    add the delta to the fixed block (slots 1 and 2) and the cavity block; ``_write_points``;
            suspend the wire / bundle chains bound to a moved point (below); move the clone points; fire the
            callbacks; resume.
    ROTATE  rotate both blocks about the housing's position; ``_write_points``; suspend; rotate the clone
            points; the angles; fire the callbacks; resume.
    ANGLES  PLAIN: a cavity's new quaternion is ``compose(its quaternion, delta)``, its Euler angles come from
            that matrix (YXZ, kept within 180 degrees of the previous values), its terminal and its seal take
            the cavity's values; the housing seal turns by its own formula. There is no OBB step: the peg board
            has no part geometry to align against. The strings ``quat_pegboard`` / ``angle_pegboard`` are
            written into the owners' rows, one ``batch_update`` per table.
    CHAINS  A wire or bundle chain bound to several of the moved points (a seated terminal's attach point, its
            stub and its cavity's stub are the same wire's three points) used to be told ``suspend_updates``
            before the points moved and ``resume_updates`` after, so it rebuilt once. Still so:
            ``rope_pull_handler.chains_bound_to_point`` is asked for every moved point (and every point that
            follows a pooled root by ``Point.attach``), and the callbacks run between the suspend and the
            resume.
    CALLBACKS  The clone points' callbacks first, then the pooled points': the cavity points, the terminal
            points, the seals (the housing's, then each cavity's), the wire-side points. The values of every
            slot are final before the first one fires.
    SEALS   When a seal's point is attached to its owner's seal position (a housing seal, a seal on a terminal),
            the old cascade moved the seal's Point, which forwards to the root WITHOUT firing the root's
            callbacks, so the follower kept its old coordinates and the next frame started from them: the
            seal jumped. Now both rows are in the pool and both are moved by the same arithmetic, the root's
            callbacks fire (they copy the root into its followers), and the follower is registered too.

THE MOVE AND THE ROTATE (schematic)
    MOVE    add the delta to the cavity block; ``_write_points``; fire the callbacks.
    ROTATE  at exactly 180 degrees the layout is not a plain rotation (``CavityGeometry.point_at_180``): each
            stored point has its own Z correction (``z_shift_at_180``: the cavity's name anchor, the end of
            the terminal's wire stub, the terminal's own point). ``PJTHousing._update_angle2d`` says whether the
            rotation starts from 180 or ends at 180; the correction is taken off the whole cavity block before
            the rotation in the first case and put on after it in the second. Then ``_write_points`` and the
            callbacks, cavity by cavity in the order cavity, terminal wire point, terminal (the terminal's
            callback reads its wire point to size the stub). The housing's own ``Angle`` is not pooled.

BINDING (what calls what; the columns are the ones in the layouts)
    allocation (``PJTTables.load``, a new housing)   every row that exists is bound and seeded.
    a point column written          ``update`` of the housings, cavities and terminals tables call
                                    ``column_changed`` (``HOUSING_POINT_COLUMNS`` / ``CAVITY_POINT_COLUMNS`` /
                                    ``TERMINAL_POINT_COLUMNS`` in each view's module). A terminal that is in no
                                    cavity (a free terminal) has no slots: the column is ignored.
    a seal row                      ``PJTSealsTable.insert`` / ``update`` call ``seal_changed``: the housing's seal
                                    binds slot 1 of the fixed block (and its angle), a seal on a terminal or a
                                    plug binds its cavity's slot 5.
    a terminal's ``cavity_id``      ``PJTTerminalsTable.update`` calls ``terminal_moved``: the points leave the
                                    old cavity's slots (a slot that holds something else is left alone) and take
                                    the new cavity's, so a free terminal that is seated follows its housing.
    a point row deleted             ``PJTPointPegboard.delete`` / ``PJTPoint2D.delete`` unbind the row.
    (The 3D view does the same for a terminal's ``cavity_id`` and ignores the point columns of a free terminal:
    ``SlotPools3D.terminal_moved``, ``HousingSlots3D.terminal_left`` / ``terminal_arrived``, added 2026-11-18.)
    angle owners                    resolved by pull and re-checked by the plan, as in section 7.

WHAT IS DIFFERENT FROM THE OLD CASCADES
    * A move or a rotate carries EVERY slot of the housing's blocks, including slots whose owner is absent
      (an empty cavity's wire points, a cavity's terminal point, a terminal's seal position, which the old
      peg board cascade never moved). The old schematic cascade skipped a terminal whose own point was not made.
    * The seals that are attached move correctly (see SEALS above).
    * The values are final before the first callback, and the peg board's clone points' callbacks fire first.
    * ``PJTHousing._find_child_points_pegboard`` is gone (the slots' plan finds the clones).
    * Results are float64 arithmetic stored as float32; they agree with the old results to 1.8e-4 mm for
      points and 3e-5 for angles.

WHAT WAS CHECKED, AND WHAT WAS NOT
    Throwaway scripts (outside the repo), interpreted Python 3.11, the real ``Point`` / ``Angle`` classes, the
    real slot classes and the real ``PJTHousing`` cascade methods of git HEAD against the new ones, on two
    identical random worlds with stand-in tables:
      peg board   30 worlds x 6 random moves and rotates, inside a gesture and outside one: 1,926 point pairs
                  (442 of them clone points) agree to 1.8e-4 mm, 1,486 angle values to 3e-5; every pooled row
                  equals its database cache exactly; every point the old cascade fired fires in the new one;
                  chains are suspended and resumed in balance, and fire only while suspended; shared rows,
                  cavities with and without terminals, terminal seals, plugs and attached seals were in the
                  worlds (the attached ones are compared with the old cascade run on unattached copies,
                  because the old cascade is wrong for them).
      schematic   40 worlds x 10 random moves and Y rotations, 54 of them to exactly 180 and many from it:
                  1,150 point pairs agree to 1.5e-4 mm, the callback ORDER is identical in all 40, the stored
                  quaternion is identical.
      lifecycle   38 checks: cavities created late, a ``Point`` that existed before its row got a slot, a
                  column that changes, an alias that is handed over, a deleted row, a seal that belongs to
                  nothing yet, a free terminal, a terminal seated / moved / taken out, release and reuse.
      timing      100 cavities, 70 % with a terminal, one frame (before -> after): peg board rotate
                  489 ms -> 5.9 ms, move 5.6 ms -> 3.4 ms; schematic rotate 2.4 ms -> 1.5 ms, move 1.5 ms ->
                  0.45 ms. These leave out the per-point listeners (a wire rebuild, a database write) that a
                  real callback runs.
    NOT checked: the app, the real ``PJTTables.load``, ``PJTHousingsTable.insert`` / ``update_cavities`` and
    the table ``update`` hooks against a real database, the real ``rope_pull_handler`` (a stand-in with the
    same ``chains_bound_to_point`` was used), a compiled build.

OPEN WORK
    * The peg board's seal followers are registered with the pool and their ``_data`` is the pool row; a
      follower that existed (as a delegator) before its row had a slot is not moved into the pool.
    * A terminal that is deleted keeps its slots bound until its point rows are deleted or the housing is.
    * The notes of section 14 (the database cache written every frame, one callback per ``Point``) apply to the
      two views too.
"""

from typing import Any, TYPE_CHECKING, Iterable as _Iterable, Union as _Union

import ast
import math
import numpy as np
import weakref
from PySide6 import QtWidgets

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .. import id_generator as _id_generator
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from . import housing_slots as _housing_slots
from . import housing_slots_pegboard as _housing_slots_pegboard
from . import housing_slots_schematic as _housing_slots_schematic
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import cavity_layout as _cavity_layout
from . import pjt_cover as _pjt_cover
from . import pjt_tpa_lock as _pjt_tpa_lock
from . import pjt_cpa_lock as _pjt_cpa_lock
from . import pjt_seal as _pjt_seal
from . import pjt_boot as _pjt_boot
from . import pjt_cavity as _pjt_cavity
from . import pjt_point2d as _pjt_point2d
from . import pjt_point3d as _pjt_point3d
from . import pjt_point_pegboard as _pjt_point_pegboard
from ..global_db import housing as _housing
from .mixins import (
    NameMixin, NameControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    VisiblePegboardMixin,
    NotesMixin, NotesControl,
    Position2DMixin, Position2DControl,
    Position3DMixin, Position3DControl,
    PositionPegboardMixin, PositionPegboardControl,
    TablePositionPegMixin,
    TableHiddenMixin,
    Angle2DMixin, Angle2DControl,
    Angle3DMixin, Angle3DControl,
    AnglePegboardMixin, AnglePegboardControl,
    SmoothMixin, SmoothControl,
    Scale3DMixin, Scale3DControl,
    ScalePegboardMixin, ScalePegboardControl
)
from ... import check_types as _check_types
from ...crash_dump import capturable, dump_property

if TYPE_CHECKING:
    # from . import pjt_accessory as _pjt_accessory
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire as _pjt_wire
    from ..global_db import housing as _housing
    from ...objects import housing as _housing_obj
    from ... import ui as _ui


@_check_types.do
def _obb_face_direction(
        current_obb: np.ndarray,
        local_obb: np.ndarray,
        face_idx: int) -> np.ndarray | None:
    """Return the normalized outward normal of *face_idx* using *current_obb*.

    Face membership is determined by sorting *local_obb* corners along the
    face axis (axis 0 → faces 0/1, axis 1 → 2/3, axis 2 → 4/5).
    The same corner indices are then read from *current_obb* (fully rotated).
    """
    axis = face_idx // 2
    sign = face_idx % 2
    sorted_i = np.argsort(local_obb[:, axis])
    corner_i = sorted_i[:4] if sign == 0 else sorted_i[4:]
    center = current_obb.mean(axis=0)
    fc = current_obb[corner_i].mean(axis=0) - center
    n = float(str(np.linalg.norm(fc)))

    return (fc / n) if n > 1e-8 else None


@_check_types.do
def _euler_from_matrix_continuous(
        rot_mat: np.ndarray,
        prev_euler_deg: tuple[float] | None) -> list[float, float, float]:
    """YXZ Euler decomposition matching :meth:`Quaternion.as_euler`.

    *rot_mat* columns are ``[right, up, forward]``.  Each angle is
    continuity-wrapped to stay within ±180° of the corresponding value in
    *prev_euler_deg* so the displayed values never jump.
    """
    pitch = float(np.degrees(np.arcsin(np.clip(-rot_mat[1, 2], -1.0, 1.0))))
    yaw = float(np.degrees(np.arctan2(rot_mat[0, 2], rot_mat[2, 2])))
    roll = float(np.degrees(np.arctan2(rot_mat[1, 0], rot_mat[1, 1])))
    result = [pitch, yaw, roll]

    if prev_euler_deg and not any(math.isnan(v) for v in prev_euler_deg):
        for i in range(3):
            while result[i] - prev_euler_deg[i] > 180.0:
                result[i] -= 360.0
            while result[i] - prev_euler_deg[i] < -180.0:
                result[i] += 360.0

    return result


class PJTHousingsTable(PJTTableBase):
    """Represent a PJT housings table in :mod:`harness_designer.database.project_db.pjt_housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_housings'

    _control: "PJTHousingControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTHousingControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTHousingControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe: "_ui.MainFrame") -> None:
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTHousingControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import housings

        return housings.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import housings

        housings.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import housings

        housings.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTHousing"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTHousing']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTHousing(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTHousing":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTHousing`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTHousing or item in self:
                return PJTHousing(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def update(self, db_id: int | bytes, **kwargs: dict[str, Any]) -> None:
        """Write columns of a housing row. A change of one of its point-id columns (an accessory's
        point) rebinds the matching slot of the housing's pooled storage (see this module's docstring, section 6).

        :param db_id: The row id.
        :type db_id: int | bytes
        :param kwargs: Column names and their new values.
        :type kwargs: dict[str, Any]
        """
        super().update(db_id, **kwargs)

        columns = {name: value for name, value in kwargs.items()
                   if name in _housing_slots.HOUSING_POINT_COLUMNS}

        if columns:
            self.db.slot_pools3d.column_changed('pjt_housings', db_id, columns)

        columns = {name: value for name, value in kwargs.items()
                   if name in _housing_slots_pegboard.HOUSING_POINT_COLUMNS}

        if columns:
            self.db.slot_pools_pegboard.column_changed('pjt_housings', db_id, columns)

        columns = {name: value for name, value in kwargs.items()
                   if name in _housing_slots_schematic.HOUSING_POINT_COLUMNS}

        if columns:
            self.db.slot_pools_schematic.column_changed('pjt_housings', db_id, columns)

    @_check_types.do
    def insert(self, part_id: bytes, name: str, position3d_id: bytes | None = None,
               position2d_id: bytes | None = None, position_pegboard_id: bytes | None = None) -> "PJTHousing":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: bytes

        :param name: Name for the part.
        :type name: str

        :param position3d_id: 3D position id.
        :type position3d_id: bytes | None

        :param position2d_id: 2D position id.
        :type position2d_id: bytes | None

        :param position_pegboard_id: pegboard position id.
        :type position_pegboard_id: bytes | None

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTHousing`
        """

        if position2d_id is None:
            position2d = self.db.pjt_points2d_table.insert(0.0, 0.0, 0.0)
            position2d_id = position2d.db_id
        else:
            position2d = self.db.pjt_points2d_table[position2d_id]

        if position3d_id is None:
            position3d = self.db.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            position3d_id = position3d.db_id

        else:
            position3d = self.db.pjt_points3d_table[position3d_id]

        if position_pegboard_id is None:
            position_pegboard = self.db.pjt_points_pegboard_table.insert(position3d.x, 0.0, position3d.z)
            position_pegboard_id = position_pegboard.db_id
        else:
            position_pegboard = self.db.pjt_points_pegboard_table[position_pegboard_id]

        db_id = PJTTableBase.insert(
            self, name=name, point3d_id=position3d_id, point2d_id=position2d_id,
            point_pegboard_id=position_pegboard_id, part_id=part_id,
            cover_point3d_id=None, seal_point3d_id=None, seal_point_pegboard_id=None,
            boot_point3d_id=None, tpa_lock_1_point3d_id=None, tpa_lock_2_point3d_id=None,
            cpa_lock_point3d_id=None, table_point_peg_id=None, table_hidden=0,
            quat_pegboard='[1.0, 0.0, 0.0, 0.0]', angle_pegboard='[0.0, 0.0, 0.0]',
            scale3d_id=None, scale_pegboard_id=None, notes='',
            quat2d='[1.0, 0.0, 0.0, 0.0]', angle2d='[0.0, 0.0, 0.0]',
            quat3d='[1.0, 0.0, 0.0, 0.0]', angle3d='[0.0, 0.0, 0.0]',
            is_visible2d=1, is_visible3d=1, is_visible_pegboard=1, smooth=None)

        db_obj = PJTHousing(self, db_id)

        # Every anchor type that can own a peg-board data-table overlay
        # gets its own row created right here, at insert time -- not
        # lazily on first "Show Table" click (see ``objects_pegboard.
        # base_pegboard.BasePegboard.show_table``, which still handles a
        # legacy row from before this wiring existed). Placed at this
        # housing's own just-created position -- no live view/AABB data
        # is available at this DB layer for a real obstacle-avoiding
        # search (see ``objects.objects_pegboard.table_placement``),
        # so this is a naive placeholder the user can drag elsewhere.
        from . import pjt_pegboard_table as _pjt_pegboard_table

        table_point_id = db_obj.table_position_peg_id
        self.db.pjt_pegboard_tables_table.insert(
            table_point_id, _point.Point(position_pegboard.x, 0.0, position_pegboard.z),
            _pjt_pegboard_table.DEFAULT_TABLE_WIDTH, _pjt_pegboard_table.DEFAULT_TABLE_HEIGHT)

        point3d = _point.Point(position3d.x, position3d.y, position3d.z)

        # Add every cavity from the part to the project -- batched: one
        # SELECT for every cavity this housing's own catalog part has
        # (keyed by the housing's own part_id -- the global cavities
        # table has no concept of a project housing at all, only global
        # housing parts), two vectorized numpy arrays (position3d,
        # position_pegboard) built from it, and one executemany() per
        # table instead of a per-cavity PJTCavitiesTable.insert() loop
        # (which does its own 4 individual round trips per cavity --
        # a point3d insert, a point2d insert, a point_pegboard insert,
        # and the cavity row insert itself). Confirmed 2026-09-07
        # (Kevin): a housing can have 100+ cavities, so doing this one
        # row at a time is real, measurable overhead.
        self.db.global_db.cavities_table.execute(
            'SELECT id, name, point3d, aabb, obb FROM cavities WHERE housing_id = ?;',
            (part_id,))
        g_rows = self.db.global_db.cavities_table.fetchall()

        # Set the stack-geometry cache directly, same reasoning as the
        # cavity_geometry cache below -- unconditionally (unlike that
        # one, this is meaningful even with zero cavities, e.g. a
        # housing part with none defined yet).
        db_obj._stored_stack_geometry = _cavity_layout.compute_stack_geometry(len(g_rows))  # NOQA

        if g_rows:
            g_ids = [row[0] for row in g_rows]
            g_names = [row[1] for row in g_rows]

            # Local offset (housing-frame) for every cavity, straight
            # from the catalog -- not a project pjt_*.position3d value.
            local_point3d = np.array(
                [ast.literal_eval(row[2]) for row in g_rows], dtype=np.float64)  # NOQA

            local_aabbs = np.array(
                [ast.literal_eval(row[3]) for row in g_rows], dtype=np.float64)  # NOQA

            local_obbs = np.array(
                [ast.literal_eval(row[4]) for row in g_rows], dtype=np.float64)  # NOQA

            h_position3d = np.array(
                [position3d.x, position3d.y, position3d.z], dtype=np.float64)

            h_position_pegboard = np.array(
                [position_pegboard.x, position_pegboard.y, position_pegboard.z],
                dtype=np.float64)

            h_position2d = np.array(
                [position2d.x, position2d.y, position2d.z],
                dtype=np.float64)

            n = len(g_rows)

            # Every cavity's own full schematic geometry (slot position,
            # name-label position/hit-box, terminal hit-box, "("
            # bracket/wire-stub-cylinder position -- see
            # geometry.cavity_layout.compute_housing_cavity_geometry's
            # own docstring for exactly what's knowable this early,
            # before any terminal is ever seated) -- computed ONCE,
            # here, and cached directly on db_obj (see PJTHousing.
            # cavity_geometry) so objects_schematic/cavity.py's Cavity/
            # objects_schematic/terminal.py's Terminal never need to
            # compute or look any of this up themselves. g_names doesn't
            # need to be pre-sorted -- natural-sort-by-name stacking
            # order is handled inside compute_housing_cavity_geometry
            # itself, and the result comes back in the SAME order as
            # g_names (so cavity_geometries[i] is g_rows[i]'s own
            # geometry, matching g_ids[i]/new_cavity_ids[i] below).
            cavity_geometries = _cavity_layout.compute_housing_cavity_geometry(g_names)

            # geo.name_position, NOT geo.position (this cavity's own SLOT
            # center) -- objects_schematic/cavity.py's Cavity has no
            # render() override, so whatever lands in point2d here IS
            # this cavity's own literal render anchor for its name label
            # (self._position, read straight from db_obj.position2d --
            # see that class's own docstring). geo.position would put the
            # label at the slot's own center instead of its own name
            # anchor (outside the housing, on the pin-edge side).
            # The schematic plane is X/Z -- geo.name_position is (x, z), so Y
            # is 0.0 here, same as the housing's own position2d.
            local_point2d = np.array(
                [[geo.name_position[0], 0.0, geo.name_position[1]]
                 for geo in cavity_geometries], dtype=np.float64)

            # No rotation -- a housing has no rotation at the point its
            # cavities are first created.
            position3d_arr = local_point3d + h_position3d
            position2d_arr = local_point2d + h_position2d
            aabb_arr = local_aabbs + h_position3d
            obb_arr = local_obbs + h_position3d

            # Peg-board: X/Z pick up the housing's own peg-board X/Z;
            # Y is NOT combined with the housing's own peg-board Y
            # (always 0.0, board-locked) -- a cavity's real local
            # height relative to its housing is honored as-is.
            position_pegboard_arr = local_point3d.copy()
            position_pegboard_arr[:, 0] += h_position_pegboard[0]
            position_pegboard_arr[:, 2] += h_position_pegboard[2]

            new_point3d_ids = [
                _id_generator.generate_project_row_id(self._con, self.project_id).bytes
                for _ in range(n)]

            new_point2d_ids = [
                _id_generator.generate_project_row_id(self._con, self.project_id).bytes
                for _ in range(n)]

            new_peg_ids = [
                _id_generator.generate_project_row_id(self._con, self.project_id).bytes
                for _ in range(n)]

            new_cavity_ids = [
                _id_generator.generate_project_row_id(self._con, self.project_id).bytes
                for _ in range(n)]

            # Every row below is built complete (every column, id included)
            # so PJTTableBase.batch_insert can write it with no read-back --
            # see that method's own docstring. Points first, cavities last
            # (commit=False on everything but the last call, so all four
            # tables land in ONE shared commit): a cavity row stores its own
            # point rows' ids, so those rows must exist in this same
            # transaction before the cavity row referencing them is built,
            # even though nothing here waits on a database-assigned id --
            # every id is already generated in Python (_id_generator) before
            # any of these INSERTs run.
            points3d_table = self.db.pjt_points3d_table
            points3d_table.batch_insert([
                {'id': new_point3d_ids[i], 'x': float(position3d_arr[i, 0]),
                 'y': float(position3d_arr[i, 1]), 'z': float(position3d_arr[i, 2]),
                 'parent_point_id': None}
                for i in range(n)], commit=False)

            points2d_table = self.db.pjt_points2d_table
            points2d_table.batch_insert([
                {'id': new_point2d_ids[i], 'x': float(position2d_arr[i, 0]),
                 'y': float(position2d_arr[i, 1]), 'z': float(position2d_arr[i, 2]),
                 'parent_point_id': None}
                for i in range(n)], commit=False)

            points_pegboard_table = self.db.pjt_points_pegboard_table
            points_pegboard_table.batch_insert([
                {'id': new_peg_ids[i], 'x': float(position_pegboard_arr[i, 0]),
                 'y': float(position_pegboard_arr[i, 1]), 'z': float(position_pegboard_arr[i, 2]),
                 'parent_point_id': None}
                for i in range(n)], commit=False)

            aabb_str = [str([[float(str(item)) for item in items] for items in aabb_arr[i].tolist()]) for i in range(n)]
            obb_str = [str([[float(str(item)) for item in items] for items in obb_arr[i].tolist()]) for i in range(n)]

            housing_ids = [db_id] * n

            # Every column the schema declares beyond the ones this housing
            # actually knows yet, set to the exact same value the database's
            # own DEFAULT clause would have used (create_database/
            # cavities.py's pjt_table definition) -- so behavior is
            # identical to the old read-back path, just without the read.
            cavities_table = self.db.pjt_cavities_table
            cavities_table.batch_insert([
                {'id': new_cavity_ids[i], 'part_id': g_ids[i], 'name': g_names[i],
                 'point2d_id': new_point2d_ids[i], 'point3d_id': new_point3d_ids[i],
                 'terminal_point3d_id': None, 'wire_point3d_id': None,
                 'point_pegboard_id': new_peg_ids[i], 'terminal_point_pegboard_id': None,
                 'wire_point_pegboard_id': None, 'housing_id': housing_ids[i],
                 'notes': '', 'quat2d': '[1.0, 0.0, 0.0, 0.0]', 'angle2d': '[0.0, 0.0, 0.0]',
                 'quat3d': '[1.0, 0.0, 0.0, 0.0]', 'angle3d': '[0.0, 0.0, 0.0]',
                 'quat_pegboard': '[1.0, 0.0, 0.0, 0.0]', 'angle_pegboard': '[0.0, 0.0, 0.0]',
                 'is_visible2d': 1, 'is_visible3d': 0, 'is_visible_pegboard': 0,
                 'aabb': aabb_str[i], 'obb': obb_str[i]}
                for i in range(n)])  # commit=True (default): this is the batch's one shared commit

            # The housing's pooled slots for these cavities, taken now: before
            # anything builds a Point or an Angle for them (see this file's docstring, section 5).
            db_obj._slots3d.cavities_created()  # NOQA
            db_obj._slots_pegboard.cavities_created()  # NOQA
            db_obj._slots_schematic.cavities_created()  # NOQA

            # Set the geometry cache directly -- see PJTHousing.
            # cavity_geometry's own docstring for why: everything needed
            # to build it was just computed above anyway, so there's no
            # reason to let the lazy property recompute it from scratch
            # (which would also mean re-measuring every cavity name's
            # own rendered width/height a second time).
            db_obj._stored_cavity_geometry = {  # NOQA
                new_cavity_ids[i]: cavity_geometries[i] for i in range(n)}

        pos = db_obj.cover_position3d
        pos += point3d

        pos = db_obj.seal_position3d
        pos += point3d

        pos = db_obj.boot_position3d
        pos += point3d

        pos = db_obj.tpa_lock_1_position3d
        pos += point3d

        pos = db_obj.tpa_lock_2_position3d
        pos += point3d

        pos = db_obj.cpa_lock_position3d
        pos += point3d

        return db_obj


@capturable()
class PJTHousing(PJTEntryBase, NameMixin, PartMixin, Position2DMixin, Position3DMixin,
                 PositionPegboardMixin, TablePositionPegMixin, TableHiddenMixin,
                 Visible3DMixin, Visible2DMixin, VisiblePegboardMixin, NotesMixin,
                 Angle2DMixin, Angle3DMixin, AnglePegboardMixin,
                 SmoothMixin, Scale3DMixin, ScalePegboardMixin):
    """Represent a PJT housing in :mod:`harness_designer.database.project_db.pjt_housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTHousingsTable = None

    @_check_types.do
    def __init__(self, table: PJTHousingsTable, db_id: bytes):
        """Initialise the housing row object and take its pooled 3D slots (allocated when the
        project was loaded, or now for a housing that was just added; see this module's
        docstring, section 5).

        :param table: The housings table.
        :type table: :class:`PJTHousingsTable`
        :param db_id: The row id.
        :type db_id: bytes
        """
        super().__init__(table, db_id)

        self._slots3d = table.db.slot_pools3d.housing(db_id)
        self._slots_pegboard = table.db.slot_pools_pegboard.housing(db_id)
        self._slots_schematic = table.db.slot_pools_schematic.housing(db_id)

    @_check_types.do
    def delete(self) -> None:
        """Delete this housing row -- first cascading to every accessory
        attached directly to it (boot/cover/cpa_lock/tpa_locks/seal),
        since none of those can meaningfully exist without their own
        housing.

        Each accessory's own ``delete()`` (plain ``PJTEntryBase.delete()``
        for boot/cover/cpa_lock/tpa_lock; ``PJTSeal`` also has no
        override) never touches the shared point it reuses from this
        housing's own ``boot_point3d_id``/``cover_point3d_id``/
        ``cpa_lock_point3d_id``/``tpa_lock_1_point3d_id``/
        ``tpa_lock_2_point3d_id``/``seal_point3d_id``/
        ``seal_point_pegboard_id`` columns -- see
        ``PJTPoint3D.is_referenced()``/``PJTPointPegboard.is_referenced()``'s
        own Phase 2/3 entries. Accessories are deleted BEFORE this
        housing's own row (not after): with every FK in the schema set
        to ``NO ACTION`` (see the "Safe point-deletion" design spec in
        TODO.md), a backend that actually enforces foreign keys (MySQL/
        InnoDB, unlike this project's SQLite connector) would reject
        deleting a still-referenced parent row out from under its
        children's own ``housing_id`` column.

        This housing's own seal is only ever the housing-level (MAT)
        kind -- a terminal-seated seal (SWS/single-wire-seal) lives on
        ``PJTTerminal.seal`` instead, cascaded from ``PJTCavity.delete()``
        -> ``PJTTerminal.delete()`` below.

        Also cascades to every cavity this housing owns (each cavity's
        own ``delete()`` further cascades to its seated terminal, and
        that terminal's own seal) -- a cavity is structural and never
        independently deletable by the user, but always goes away when
        its housing does. Also cascades to this housing's own peg-board
        data-table overlay row, if it has one (Phase 4, see
        ``TablePositionPegMixin.delete_table_overlay``'s own docstring).

        Phases 2 (2026-09-02, boot/cover/cpa_lock/tpa_locks), 3
        (2026-09-02, seal), 4 (2026-09-02, peg-board table overlay), and
        5 (2026-09-02, cavities/terminals) of the point-safety-check
        rollout, see TODO.md.
        """
        for accessory in (
            self.boot, self.cover, self.cpa_lock, self.tpa_lock1, self.tpa_lock2, self.seal,
        ):
            if accessory is not None:
                accessory.delete()

        for cavity in self.cavities:
            cavity.delete()

        self.delete_table_overlay()

        super().delete()

        self._table.db.slot_pools3d.release(self._db_id)
        self._table.db.slot_pools_pegboard.release(self._db_id)
        self._table.db.slot_pools_schematic.release(self._db_id)

    @_check_types.do
    def update_cavities(self) -> None:
        for cavity in self.cavities:
            if cavity is not None:
                return

        position2d = self.position2d
        position3d = self.position3d
        position_pegboard = self.position_pegboard

        db_obj = self

        # Add every cavity from the part to the project -- batched: one
        # SELECT for every cavity this housing's own catalog part has
        # (keyed by the housing's own part_id -- the global cavities
        # table has no concept of a project housing at all, only global
        # housing parts), two vectorized numpy arrays (position3d,
        # position_pegboard) built from it, and one executemany() per
        # table instead of a per-cavity PJTCavitiesTable.insert() loop
        # (which does its own 4 individual round trips per cavity --
        # a point3d insert, a point2d insert, a point_pegboard insert,
        # and the cavity row insert itself). Confirmed 2026-09-07
        # (Kevin): a housing can have 100+ cavities, so doing this one
        # row at a time is real, measurable overhead.
        self.table.db.global_db.cavities_table.execute(
            'SELECT id, name, point3d, aabb, obb FROM cavities WHERE housing_id = ?;',
            (self.part_id,))
        g_rows = self.table.db.global_db.cavities_table.fetchall()

        # Set the stack-geometry cache directly, same reasoning as the
        # cavity_geometry cache below -- unconditionally (unlike that
        # one, this is meaningful even with zero cavities, e.g. a
        # housing part with none defined yet).
        db_obj._stored_stack_geometry = _cavity_layout.compute_stack_geometry(len(g_rows))  # NOQA

        if g_rows:
            g_ids = [row[0] for row in g_rows]
            g_names = [row[1] for row in g_rows]

            # Local offset (housing-frame) for every cavity, straight
            # from the catalog -- not a project pjt_*.position3d value.
            local_point3d = np.array(
                [ast.literal_eval(row[2]) for row in g_rows], dtype=np.float64)  # NOQA

            local_aabbs = np.array(
                [ast.literal_eval(row[3]) for row in g_rows], dtype=np.float64)  # NOQA

            local_obbs = np.array(
                [ast.literal_eval(row[4]) for row in g_rows], dtype=np.float64)  # NOQA

            h_position3d = np.array(
                [position3d.x, position3d.y, position3d.z], dtype=np.float64)

            h_position_pegboard = np.array(
                [position_pegboard.x, position_pegboard.y, position_pegboard.z],
                dtype=np.float64)

            h_position2d = np.array(
                [position2d.x, position2d.y, position2d.z],
                dtype=np.float64)

            n = len(g_rows)

            # Every cavity's own full schematic geometry (slot position,
            # name-label position/hit-box, terminal hit-box, "("
            # bracket/wire-stub-cylinder position -- see
            # geometry.cavity_layout.compute_housing_cavity_geometry's
            # own docstring for exactly what's knowable this early,
            # before any terminal is ever seated) -- computed ONCE,
            # here, and cached directly on db_obj (see PJTHousing.
            # cavity_geometry) so objects_schematic/cavity.py's Cavity/
            # objects_schematic/terminal.py's Terminal never need to
            # compute or look any of this up themselves. g_names doesn't
            # need to be pre-sorted -- natural-sort-by-name stacking
            # order is handled inside compute_housing_cavity_geometry
            # itself, and the result comes back in the SAME order as
            # g_names (so cavity_geometries[i] is g_rows[i]'s own
            # geometry, matching g_ids[i]/new_cavity_ids[i] below).
            cavity_geometries = _cavity_layout.compute_housing_cavity_geometry(g_names)

            # geo.name_position, NOT geo.position (this cavity's own SLOT
            # center) -- objects_schematic/cavity.py's Cavity has no
            # render() override, so whatever lands in point2d here IS
            # this cavity's own literal render anchor for its name label
            # (self._position, read straight from db_obj.position2d --
            # see that class's own docstring). geo.position would put the
            # label at the slot's own center instead of its own name
            # anchor (outside the housing, on the pin-edge side).
            # The schematic plane is X/Z -- geo.name_position is (x, z), so Y
            # is 0.0 here, same as the housing's own position2d.
            local_point2d = np.array(
                [[geo.name_position[0], 0.0, geo.name_position[1]]
                 for geo in cavity_geometries], dtype=np.float64)

            # No rotation -- a housing has no rotation at the point its
            # cavities are first created.
            position3d_arr = local_point3d + h_position3d
            position2d_arr = local_point2d + h_position2d
            aabb_arr = local_aabbs + h_position3d
            obb_arr = local_obbs + h_position3d

            # Peg-board: X/Z pick up the housing's own peg-board X/Z;
            # Y is NOT combined with the housing's own peg-board Y
            # (always 0.0, board-locked) -- a cavity's real local
            # height relative to its housing is honored as-is.
            position_pegboard_arr = local_point3d.copy()
            position_pegboard_arr[:, 0] += h_position_pegboard[0]
            position_pegboard_arr[:, 2] += h_position_pegboard[2]

            new_point3d_ids = [
                _id_generator.generate_project_row_id(
                    self.table._con, self.table.project_id).bytes  # NOQA
                for _ in range(n)]

            new_point2d_ids = [
                _id_generator.generate_project_row_id(
                    self.table._con, self.table.project_id).bytes  # NOQA
                for _ in range(n)]

            new_peg_ids = [
                _id_generator.generate_project_row_id(
                    self.table._con, self.table.project_id).bytes  # NOQA
                for _ in range(n)]

            new_cavity_ids = [
                _id_generator.generate_project_row_id(
                    self.table._con, self.table.project_id).bytes  # NOQA
                for _ in range(n)]

            # Every row below is built complete (every column, id included)
            # so PJTTableBase.batch_insert can write it with no read-back --
            # see that method's own docstring. Points first, cavities last
            # (commit=False on everything but the last call, so all four
            # tables land in ONE shared commit): a cavity row stores its own
            # point rows' ids, so those rows must exist in this same
            # transaction before the cavity row referencing them is built,
            # even though nothing here waits on a database-assigned id --
            # every id is already generated in Python (_id_generator) before
            # any of these INSERTs run.
            points3d_table = self.table.db.pjt_points3d_table
            points3d_table.batch_insert([
                {'id': new_point3d_ids[i], 'x': float(position3d_arr[i, 0]),
                 'y': float(position3d_arr[i, 1]), 'z': float(position3d_arr[i, 2]),
                 'parent_point_id': None}
                for i in range(n)], commit=False)

            points2d_table = self.table.db.pjt_points2d_table
            points2d_table.batch_insert([
                {'id': new_point2d_ids[i], 'x': float(position2d_arr[i, 0]),
                 'y': float(position2d_arr[i, 1]), 'z': float(position2d_arr[i, 2]),
                 'parent_point_id': None}
                for i in range(n)], commit=False)

            points_pegboard_table = self.table.db.pjt_points_pegboard_table
            points_pegboard_table.batch_insert([
                {'id': new_peg_ids[i], 'x': float(position_pegboard_arr[i, 0]),
                 'y': float(position_pegboard_arr[i, 1]), 'z': float(position_pegboard_arr[i, 2]),
                 'parent_point_id': None}
                for i in range(n)], commit=False)

            aabb_str = [str([
                [float(str(item)) for item in items]
                for items in aabb_arr[i].tolist()]) for i in range(n)]

            obb_str = [str([
                [float(str(item)) for item in items]
                for items in obb_arr[i].tolist()]) for i in range(n)]

            housing_ids = [self.db_id] * n

            # Every column the schema declares beyond the ones this housing
            # actually knows yet, set to the exact same value the database's
            # own DEFAULT clause would have used (create_database/
            # cavities.py's pjt_table definition) -- so behavior is
            # identical to the old read-back path, just without the read.
            cavities_table = self.table.db.pjt_cavities_table
            cavities_table.batch_insert([
                {'id': new_cavity_ids[i], 'part_id': g_ids[i], 'name': g_names[i],
                 'point2d_id': new_point2d_ids[i], 'point3d_id': new_point3d_ids[i],
                 'terminal_point3d_id': None, 'wire_point3d_id': None,
                 'point_pegboard_id': new_peg_ids[i], 'terminal_point_pegboard_id': None,
                 'wire_point_pegboard_id': None, 'housing_id': housing_ids[i],
                 'notes': '', 'quat2d': '[1.0, 0.0, 0.0, 0.0]', 'angle2d': '[0.0, 0.0, 0.0]',
                 'quat3d': '[1.0, 0.0, 0.0, 0.0]', 'angle3d': '[0.0, 0.0, 0.0]',
                 'quat_pegboard': '[1.0, 0.0, 0.0, 0.0]', 'angle_pegboard': '[0.0, 0.0, 0.0]',
                 'is_visible2d': 1, 'is_visible3d': 0, 'is_visible_pegboard': 0,
                 'aabb': aabb_str[i], 'obb': obb_str[i]}
                for i in range(n)])  # commit=True (default): this is the batch's one shared commit

            # The pooled slots for the cavities just created, taken before the
            # Cavity objects below build any Point or Angle (see this file's docstring, section 5).
            self._slots3d.cavities_created()
            self._slots_pegboard.cavities_created()
            self._slots_schematic.cavities_created()

            # Set the geometry cache directly -- see PJTHousing.
            # cavity_geometry's own docstring for why: everything needed
            # to build it was just computed above anyway, so there's no
            # reason to let the lazy property recompute it from scratch
            # (which would also mean re-measuring every cavity name's
            # own rendered width/height a second time).
            db_obj._stored_cavity_geometry = {  # NOQA
                new_cavity_ids[i]: cavity_geometries[i] for i in range(n)}

            # Build every cavity's own PJTCavity/PJTPoint2D/PJTPoint3D/
            # PJTPointPegboard directly from what's already sitting in
            # the arrays above, pre-seeding every _stored_* cache the
            # same way cache_names() does -- instead of letting
            # table[id] (an existence-check query) or each lazy
            # position/name property re-fetch a row this method itself
            # just inserted. This housing's own db_obj is already known
            # (self), so housing/housing_id cost nothing either.
            #
            # Constructing the facade Cavity objects and registering
            # them with the project is NOT optional bookkeeping -- a
            # PJTCavity row with no bound Cavity facade returns None
            # from get_object(), which objects.housing.Housing.cavities
            # silently filters out, which means match_cavity_surfaces()
            # (this method's own caller in objects_3d/housing.py's
            # _set_model) never sees these cavities at all -- they stay
            # permanently unclickable/without a selection overlay until
            # the project is reloaded.
            from ...objects import cavity as _cavity

            cavities_table = self.table.db.pjt_cavities_table
            point2d_table = self.table.db.pjt_points2d_table
            point3d_table = self.table.db.pjt_points3d_table
            peg_table = self.table.db.pjt_points_pegboard_table

            new_db_objs = []

            for i in range(n):
                cavity = _pjt_cavity.PJTCavity(cavities_table, new_cavity_ids[i])
                # name/notes/part_id/housing_id/housing/terminal have no
                # local cache of their own any more (NameMixin/NotesMixin/
                # PartMixin/HousingMixin, and PJTCavity.terminal, all read
                # straight through) -- only aabb/obb and the position
                # object caches below are still worth pre-seeding.
                cavity._stored_aabb = aabb_arr[i].astype(np.float32)  # NOQA
                cavity._stored_obb = obb_arr[i].astype(np.float32)  # NOQA

                point2d = _pjt_point2d.PJTPoint2D(point2d_table, new_point2d_ids[i])
                point2d._stored_x = float(position2d_arr[i, 0])  # NOQA
                point2d._stored_y = float(position2d_arr[i, 1])  # NOQA
                point2d._stored_z = float(position2d_arr[i, 2])  # NOQA
                cavity._stored_position2d = point2d  # NOQA

                point3d = _pjt_point3d.PJTPoint3D(point3d_table, new_point3d_ids[i])
                point3d._stored_x = float(position3d_arr[i, 0])  # NOQA
                point3d._stored_y = float(position3d_arr[i, 1])  # NOQA
                point3d._stored_z = float(position3d_arr[i, 2])  # NOQA
                cavity._stored_position3d = point3d  # NOQA

                point_pegboard = _pjt_point_pegboard.PJTPointPegboard(peg_table, new_peg_ids[i])
                point_pegboard._stored_x = float(position_pegboard_arr[i, 0])  # NOQA
                point_pegboard._stored_y = float(position_pegboard_arr[i, 1])  # NOQA
                point_pegboard._stored_z = float(position_pegboard_arr[i, 2])  # NOQA
                cavity._stored_position_pegboard = point_pegboard  # NOQA

                new_db_objs.append(cavity)

            for cavity in new_db_objs:
                cavity_obj = _cavity.Cavity(self.table.db.mainframe, cavity)
                self.table.db.mainframe.project.add_cavity(cavity_obj)

            self._stored_cavities = new_db_objs

            self._after_cavities_created()

    @_check_types.do
    def _after_cavities_created(self) -> None:
        """What a housing needs once its cavities were created LATE (the part had none when the housing was placed: its model was still
        being downloaded; user, 2026-11-11), because everything was made for a housing with no cavities and an unrotated one:

        * the cavities are made at their unrotated offsets, so the housing's current rotation in each view (3D, peg board, schematic) is
          applied to them now: the angle cascade is run once from the identity rotation to the housing's own, which turns every
          cavity's position (and its angle) about the housing as a rotate gesture would;
        * the schematic view of the housing was sized for zero cavities (a very thin rectangle) and is sized again.
        """
        identity_quat = [1.0, 0.0, 0.0, 0.0]
        identity_euler = [0.0, 0.0, 0.0]

        for angle, quat_attr, euler_attr, cascade in (
                (self.angle3d, '_o_quat3d', '_o_euler3d', self._update_angle3d),
                (self.angle_pegboard, '_o_quat_pegboard', '_o_euler_pegboard', self._update_angle_pegboard),
                (self.angle2d, '_o_quat2d', '_o_euler2d', self._update_angle2d)):
            # (the sign of a quaternion does not matter: w = 1 or -1 is no rotation)
            if abs(float(angle.as_quat_float[0])) > 1.0 - 1e-6:
                continue

            setattr(self, quat_attr, list(identity_quat))
            setattr(self, euler_attr, list(identity_euler))
            cascade(angle)

        housing = self.get_object()

        if housing is not None and housing.objschematic is not None:
            housing.objschematic.refresh_size()


    @_check_types.do
    def get_object(self) -> _Union["_housing_obj.Housing", None]:
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_housing_obj.Housing`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_housing_obj.Housing") -> None:
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing_obj.Housing`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @property
    @_check_types.do
    def table(self) -> PJTHousingsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTHousingsTable`
        """
        return self._table

    _stored_cavities: list | None = None

    @property
    @dump_property(severity=2)
    @_check_types.do
    def cavities(self) -> list[_pjt_cavity.PJTCavity]:
        """Return the cavities.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_cavity.PJTCavity']
        """
        if self._stored_cavities is not None:
            return self._stored_cavities

        cavities = []

        cavity_ids = self._table.db.pjt_cavities_table.select(
            'id', housing_id=self._db_id)

        for cavity_id in cavity_ids:
            cavity = self._table.db.pjt_cavities_table[cavity_id[0]]

            cavities.append(cavity)

        self._stored_cavities = cavities
        return cavities

    @property
    @_check_types.do
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        """Return every wire seated in one of this housing's own
        cavities' terminals.

        Same ``wires`` API point every anchor type that can own a peg-
        board data-table overlay exposes identically (see
        ``pjt_bundle.PJTBundle.wires``/``pjt_transition.
        PJTTransition.wires``/``pjt_transition_branch.
        PJTTransitionBranch.wires``) -- ``objects.objects_pegboard.
        pegboard_table`` reads this without needing to know which
        concrete anchor type it's actually attached to.

        :returns: Wires seated in this housing.
        :rtype: list[:class:`_pjt_wire.PJTWire`]
        """
        res = []

        for cavity in self.cavities:
            terminal = cavity.terminal
            if terminal is None:
                continue

            # attach_position3d_id -- NOT wire_position3d_id -- is the
            # wire's own actual start_point3d_id/stop_point3d_id once
            # seated (see objects.terminal.Terminal.add_wire, which sets
            # wire.db_obj.start/stop_position3d_id straight to this
            # terminal's own attach_position3d_id). wire_position3d_id
            # becomes an INTERIOR WAYPOINT on that same wire instead
            # (tagged with its own wire_id there), never the wire's own
            # start/stop -- matching against it here found nothing
            # (confirmed 2026-09-16: zero wires listed for a housing
            # with one real wire attached).
            point_id = terminal.attach_position3d_id_raw
            if point_id is None:
                continue

            wires_table = self._table.db.pjt_wires_table
            for row in wires_table.select('id', start_point3d_id=point_id):
                res.append(wires_table[row[0]])
            for row in wires_table.select('id', stop_point3d_id=point_id):
                res.append(wires_table[row[0]])

        return res

    _stored_cavity_geometry: dict | None = None

    @property
    @_check_types.do
    def cavity_geometry(self) -> dict:
        """Every cavity's own schematic geometry (see
        ``geometry.cavity_layout.CavityGeometry``) under this housing,
        keyed by each cavity's own ``db_id`` -- ``objects_schematic/
        cavity.py``'s ``Cavity``/``objects_schematic/terminal.py``'s
        ``Terminal`` read straight from this instead of computing
        anything themselves, so neither ever depends on the schematic
        ``Housing`` VIEW object's own construction state (a real problem
        before this cache existed -- a cavity's own geometry used to be
        computed live from ``self.housing`` (the schematic view), which
        is unresolvable at this cavity's own construction time, and
        -- for a project-load housing whose cavity view objects already
        exist before its own housing view does -- unresolvable even
        later).

        Lazily computed and cached here on first access -- the
        project-load path, where this housing's cavity rows already
        exist with no insert-time context available.
        :meth:`PJTHousingsTable.insert` instead sets this cache directly
        (bypassing this lazy path) since it already has everything
        needed to build it as part of its own batched cavity insert.

        Invalidated (forcing a recompute on next access) only by
        :meth:`add_cavity`/:meth:`update_cavities` -- i.e. only when a
        cavity ROW is inserted. Nothing currently invalidates it when an
        EXISTING cavity is renamed, even though a rename changes that
        cavity's own natural-sort stack position (and so every other
        cavity's own geometry too) -- ``objects_schematic/housing.py``'s
        ``Housing`` used to react to a cavity's own ``'name'`` tag and
        force this recompute, but that whole reactive path was removed
        (2026-09-10, Kevin) pending a proper design for where this
        responsibility belongs -- see that class's own docstring. A
        cavity's own name is treated as fixed once its row exists, for
        now.
        """
        if self._stored_cavity_geometry is None:
            self._stored_cavity_geometry = self._compute_cavity_geometry()

        return self._stored_cavity_geometry

    @_check_types.do
    def _compute_cavity_geometry(self) -> dict:
        """Batch-compute every one of this housing's own cavities' own
        geometry via ``geometry.cavity_layout.
        compute_housing_cavity_geometry`` -- the lazy-path counterpart
        to :meth:`PJTHousingsTable.insert`'s own direct cache set (same
        underlying function, so the two can never independently drift
        apart). No pre-sorting needed -- natural-sort-by-name stacking
        order is handled inside that function itself, and its result
        comes back in the SAME order as the names passed in.
        """
        cavities = [c for c in self.cavities if c is not None]
        names = [c.name for c in cavities]
        geometries = _cavity_layout.compute_housing_cavity_geometry(names)

        return {c.db_id: geometry for c, geometry in zip(cavities, geometries)}

    _stored_stack_geometry: _cavity_layout.CavityStackGeometry = None

    @property
    @_check_types.do
    def stack_geometry(self) -> _cavity_layout.CavityStackGeometry:
        """This housing's own font-driven cavity slot height and
        cavity-axis/text-axis extents (see
        ``geometry.cavity_layout.CavityStackGeometry``) -- everything
        ``objects_schematic/housing.py``'s ``Housing`` needs to size its
        own rectangle, cached here the same way :attr:`cavity_geometry`
        is (and invalidated at exactly the same points -- see
        :meth:`add_cavity`/:meth:`update_cavities`, and
        :meth:`PJTHousingsTable.insert`, which sets this cache directly
        as part of its own batched cavity insert, same as it does for
        :attr:`cavity_geometry`) -- both depend on nothing but this
        housing's own cavity COUNT, never any individual cavity's own
        name, so a rename can never invalidate this one even though it
        still can (once that's implemented) invalidate
        :attr:`cavity_geometry`.
        """
        if self._stored_stack_geometry is None:
            cavities = [c for c in self.cavities if c is not None]
            self._stored_stack_geometry = _cavity_layout.compute_stack_geometry(len(cavities))

        return self._stored_stack_geometry

    _stored_terminals: list | None = None

    @property
    @dump_property(severity=2)
    @_check_types.do
    def terminals(self) -> list["_pjt_terminal.PJTTerminal"]:
        """Every seated terminal across this housing's own cavities.

        Populated as a side effect of :meth:`cache_names` -- falls back
        to walking :attr:`cavities` (each cavity's own ``.terminal``
        lazy lookup) when that hasn't been called yet.
        """
        if self._stored_terminals is not None:
            return self._stored_terminals

        terminals = []
        for cavity in self.cavities:
            if cavity is None:
                continue

            terminal = cavity.terminal
            if terminal is not None:
                terminals.append(terminal)

        self._stored_terminals = terminals
        return terminals

    @_check_types.do
    def cache_names(self) -> None:
        """Batch-fetch every cavity's own position2d and seated terminal
        under this housing, in a single query, and pre-seed the result
        straight into the real (singleton) ``PJTCavity``/``PJTPoint2D``/
        ``PJTTerminal`` instances' own caches -- ``Position2DMixin.
        _stored_position2d`` (with the ``PJTPoint2D``'s own
        ``_stored_x``/``_stored_y`` pre-seeded too) for each cavity, plus
        ``PJTTerminal.cavity``'s cross-reference cache -- so that later
        reading any of those never fires its own query. ``name`` has no
        local cache of its own any more (``NameMixin`` always reads
        straight through), and neither does ``PJTCavity.terminal`` --
        both are cheap anyway once this join's own rows are sitting in
        the row-level cache from project load.

        A housing can have several hundred cavities; the naive path
        (this housing's own ``cavities`` property, then each cavity's
        ``.position2d``, ``.terminal``) is several queries per cavity --
        ``position2d`` alone is two (one for ``point2d_id``, one to
        construct the ``PJTPoint2D`` row), before even reading ``.x``/
        ``.y`` off it. Constructs each ``PJTCavity``/``PJTPoint2D``/``PJTTerminal`` by
        calling the class directly (``PJTCavity(table, id)``/etc.)
        rather than going through ``table[id]`` -- the entry-singleton
        metaclass (see ``database/global_db/bases.py``'s
        ``_EntrySingleton``) already returns the existing cached
        instance for an id if one's alive, so this never re-queries an
        existence check the way ``TableBase.__getitem__`` does.

        Meant to run once, up front, before any per-cavity/per-terminal
        view object gets constructed -- see ``objects/housing.py``'s
        ``Housing._construct_cavities``, and
        ``objects_schematic/housing.py``'s ``Housing``/
        ``objects_schematic/cavity.py``'s ``Cavity``, both of which read
        every cavity's own ``position2d`` while building/laying out the
        schematic view.
        """
        from . import pjt_terminal as _pjt_terminal

        cavity_table = self._table.db.pjt_cavities_table
        point2d_table = self._table.db.pjt_points2d_table
        terminal_table = self._table.db.pjt_terminals_table

        # cavity.name/terminal.name are no longer selected -- NameMixin has
        # no local cache left to prime (it always reads straight through,
        # and this join's own rows are already in the row-level cache from
        # project load, so that read is cheap anyway).
        self._table.db.connector.execute(
            'SELECT cavity.id, cavity.point2d_id, point2d.x, point2d.y, point2d.z, '
            'terminal.id '
            'FROM pjt_cavities AS cavity '
            'LEFT JOIN pjt_points2d AS point2d ON point2d.id = cavity.point2d_id '
            'LEFT JOIN pjt_terminals AS terminal ON terminal.cavity_id = cavity.id '
            'WHERE cavity.housing_id = ?;',
            (self._db_id,))

        rows = self._table.db.connector.fetchall()

        cavities = []
        terminals = []

        for (cavity_id, point2d_id, point2d_x, point2d_y, point2d_z, terminal_id) in rows:
            cavity = _pjt_cavity.PJTCavity(cavity_table, cavity_id)

            if point2d_id is not None:
                point2d = _pjt_point2d.PJTPoint2D(point2d_table, point2d_id)
                point2d._stored_x = point2d_x  # NOQA
                point2d._stored_y = point2d_y  # NOQA
                point2d._stored_z = point2d_z  # NOQA
                cavity._stored_position2d = point2d  # NOQA

            if terminal_id is not None:
                terminal = _pjt_terminal.PJTTerminal(terminal_table, terminal_id)
                terminal._stored_cavity = cavity  # NOQA
                terminals.append(terminal)

            cavities.append(cavity)

        self._stored_cavities = cavities
        self._stored_terminals = terminals

    _stored_cover_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @_check_types.do
    def cover_position3d(self) -> _point.Point:
        """Return the cover position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_cover_position3d is DefaultStoredValue:
            point_id = self.cover_position3d_id
            if point_id is None:
                self._stored_cover_position3d = None
            else:
                self._stored_cover_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_cover_position3d is not None:
            if self._obj is not None:
                self._stored_cover_position3d.add_object(self._obj())
                
            point = self._stored_cover_position3d.point
        else:
            point = None
        
        return point
    
    @property
    @_check_types.do
    def cover_position3d_id(self) -> bytes:
        """Return the cover position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        point_id = self._table.select('cover_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.cover_position3d_id = point_id

        return point_id

    @cover_position3d_id.setter
    @_check_types.do
    def cover_position3d_id(self, value: bytes) -> None:
        """Set the cover position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_cover_position3d = DefaultStoredValue

        self._table.update(self._db_id, cover_point3d_id=value)
        self._populate('cover_position3d_id')

    _stored_seal_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @_check_types.do
    def seal_position3d(self) -> _point.Point:
        """Return the seal position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_seal_position3d is DefaultStoredValue:
            point_id = self.seal_position3d_id
            if point_id is None:
                self._stored_seal_position3d = None
            else:
                self._stored_seal_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_seal_position3d is not None:
            if self._obj is not None:
                self._stored_seal_position3d.add_object(self._obj())
                
            point = self._stored_seal_position3d.point
        else:
            point = None
        
        return point
    
    @property
    @_check_types.do
    def seal_position3d_id(self) -> bytes:
        """Return the seal position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        point_id = self._table.select('seal_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.seal_position3d_id = point_id

        return point_id

    @seal_position3d_id.setter
    @_check_types.do
    def seal_position3d_id(self, value: bytes) -> None:
        """Set the seal position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_seal_position3d = DefaultStoredValue

        self._table.update(self._db_id, seal_point3d_id=value)
        self._populate('seal_position3d_id')

    _stored_seal_position_pegboard: _pjt_point_pegboard.PJTPointPegboard | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def seal_position_pegboard(self) -> _point.Point:
        """Peg-board mirror of :attr:`seal_position3d`, lazily created (at
        the origin) instead of computed from real geometry.

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_seal_position_pegboard is DefaultStoredValue:
            point_id = self.seal_position_pegboard_id
            if point_id is None:
                self._stored_seal_position_pegboard = None
            else:
                self._stored_seal_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

        if self._stored_seal_position_pegboard is not None:
            if self._obj is not None:
                self._stored_seal_position_pegboard.add_object(self._obj())

            point = self._stored_seal_position_pegboard.point
        else:
            point = None

        return point

    @property
    @_check_types.do
    def seal_position_pegboard_id(self) -> bytes:
        """Return the ``pjt_points_pegboard`` row id for the peg-board
        mirror of :attr:`seal_position3d_id`, lazily creating and
        persisting it (at the origin) on first access.

        :returns: Property value.
        :rtype: bytes
        """
        point_id = self._table.select('seal_point_pegboard_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points_pegboard_table.insert(0.0, 0.0, 0.0).db_id

            self.seal_position_pegboard_id = point_id

        return point_id

    @seal_position_pegboard_id.setter
    @_check_types.do
    def seal_position_pegboard_id(self, value: bytes) -> None:
        """Set the peg-board mirror of :attr:`seal_position3d_id`.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_seal_position_pegboard = DefaultStoredValue

        self._table.update(self._db_id, seal_point_pegboard_id=value)
        self._populate('seal_position_pegboard_id')

    _stored_boot_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @_check_types.do
    def boot_position3d(self) -> _point.Point:
        """Return the boot position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_boot_position3d is DefaultStoredValue:
            point_id = self.boot_position3d_id
            if point_id is None:
                self._stored_boot_position3d = None
            else:
                self._stored_boot_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_boot_position3d is not None:
            if self._obj is not None:
                self._stored_boot_position3d.add_object(self._obj())
                
            point = self._stored_boot_position3d.point
        else:
            point = None
        
        return point
    
    @property
    @_check_types.do
    def boot_position3d_id(self) -> bytes:
        """Return the boot position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        point_id = self._table.select('boot_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.boot_position3d_id = point_id

        return point_id

    @boot_position3d_id.setter
    @_check_types.do
    def boot_position3d_id(self, value: bytes) -> None:
        """Set the boot position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_boot_position3d = DefaultStoredValue

        self._table.update(self._db_id, boot_point3d_id=value)
        self._populate('boot_position3d_id')

    _stored_tpa_lock_1_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @_check_types.do
    def tpa_lock_1_position3d(self) -> _point.Point:
        """Return the tpa_lock_1 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_tpa_lock_1_position3d is DefaultStoredValue:
            point_id = self.tpa_lock_1_position3d_id
            if point_id is None:
                self._stored_tpa_lock_1_position3d = None
            else:
                self._stored_tpa_lock_1_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_tpa_lock_1_position3d is not None:
            if self._obj is not None:
                self._stored_tpa_lock_1_position3d.add_object(self._obj())
                
            point = self._stored_tpa_lock_1_position3d.point
        else:
            point = None
        
        return point
    
    @property
    @_check_types.do
    def tpa_lock_1_position3d_id(self) -> bytes:
        """Return the tpa_lock_1 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        point_id = self._table.select('tpa_lock_1_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.tpa_lock_1_position3d_id = point_id

        return point_id

    @tpa_lock_1_position3d_id.setter
    @_check_types.do
    def tpa_lock_1_position3d_id(self, value: bytes) -> None:
        """Set the tpa_lock_1 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_tpa_lock_1_position3d = DefaultStoredValue

        self._table.update(self._db_id, tpa_lock_1_point3d_id=value)
        self._populate('tpa_lock_1_position3d_id')

    _stored_tpa_lock_2_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @_check_types.do
    def tpa_lock_2_position3d(self) -> _point.Point:
        """Return the tpa_lock_2 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_tpa_lock_2_position3d is DefaultStoredValue:
            point_id = self.tpa_lock_2_position3d_id
            if point_id is None:
                self._stored_tpa_lock_2_position3d = None
            else:
                self._stored_tpa_lock_2_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_tpa_lock_2_position3d is not None:
            if self._obj is not None:
                self._stored_tpa_lock_2_position3d.add_object(self._obj())
                
            point = self._stored_tpa_lock_2_position3d.point
        else:
            point = None
        
        return point
    
    @property
    @_check_types.do
    def tpa_lock_2_position3d_id(self) -> bytes:
        """Return the tpa_lock_2 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        point_id = self._table.select('tpa_lock_2_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.tpa_lock_2_position3d_id = point_id

        return point_id

    @tpa_lock_2_position3d_id.setter
    @_check_types.do
    def tpa_lock_2_position3d_id(self, value: bytes) -> None:
        """Set the tpa_lock_2 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_tpa_lock_2_position3d = DefaultStoredValue

        self._table.update(self._db_id, tpa_lock_2_point3d_id=value)
        self._populate('tpa_lock_2_position3d_id')

    _stored_cpa_lock_position3d: _Union["_pjt_point3d.PJTPoint3D", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @_check_types.do
    def cpa_lock_position3d(self) -> _point.Point:
        """Return the cpa_lock position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_cpa_lock_position3d is DefaultStoredValue:
            point_id = self.cpa_lock_position3d_id
            if point_id is None:
                self._stored_cpa_lock_position3d = None
            else:
                self._stored_cpa_lock_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_cpa_lock_position3d is not None:
            if self._obj is not None:
                self._stored_cpa_lock_position3d.add_object(self._obj())
                
            point = self._stored_cpa_lock_position3d.point
        else:
            point = None
        
        return point
    
    @property
    @_check_types.do
    def cpa_lock_position3d_id(self) -> bytes:
        """Return the cpa_lock position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        point_id = self._table.select('cpa_lock_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.cpa_lock_position3d_id = point_id

        return point_id

    @cpa_lock_position3d_id.setter
    @_check_types.do
    def cpa_lock_position3d_id(self, value: bytes) -> None:
        """Set the cpa_lock position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_cpa_lock_position3d = DefaultStoredValue

        self._table.update(self._db_id, cpa_lock_point3d_id=value)
        self._populate('cpa_lock_position3d_id')

    @_check_types.do
    def add_cavity(self, index: int, name: str) -> "_pjt_cavity.PJTCavity":
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :param name: Name value.
        :type name: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        cavities = self.cavities
        assert cavities[index] is None, 'Sanity Check'

        part = self.part
        cavity_part = part.cavities[index]

        if name is None:
            name = cavity_part.name

        cavity = self._table.db.pjt_cavities_table.insert(cavity_part.db_id, self.db_id)

        cavity.name = name
        self._stored_cavities = None
        self._stored_cavity_geometry = None
        self._stored_stack_geometry = None
        return cavity

    @property
    @dump_property(severity=2)
    @_check_types.do
    def seal(self) -> _pjt_seal.PJTSeal | None:
        """Return the seal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_seal.PJTSeal`
        """
        db_ids = self._table.db.pjt_seals_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    @property
    @dump_property(severity=2)
    @_check_types.do
    def cpa_lock(self) -> _pjt_cpa_lock.PJTCPALock | None:
        """Return the CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_cpa_lock.PJTCPALock`
        """
        db_ids = self._table.db.pjt_cpa_locks_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                cpa_lock = self._table.db.pjt_cpa_locks_table[db_id[0]]
            except IndexError:
                continue

            return cpa_lock

    @property
    @_check_types.do
    def tpa_lock1(self) -> _pjt_tpa_lock.PJTTPALock | None:
        """Return the TPA lock 1.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_tpa_lock.PJTTPALock`
        """
        rows = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id, idx=1)

        if rows:
            db_id = rows[0][0]
            return self._table.db.pjt_tpa_locks_table[db_id]

    @property
    @_check_types.do
    def tpa_lock2(self) -> _pjt_tpa_lock.PJTTPALock | None:
        """Return the TPA lock 2.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_tpa_lock.PJTTPALock`
        """
        rows = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id, idx=2)

        if rows:
            db_id = rows[0][0]
            return self._table.db.pjt_tpa_locks_table[db_id]

    @property
    @dump_property(severity=2)
    @_check_types.do
    def tpa_locks(self) -> list[_pjt_tpa_lock.PJTTPALock]:
        """Return the TPA locks.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_tpa_lock.PJTTPALock']
        """
        res = []
        db_ids = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                tpa_lock = self._table.db.pjt_tpa_locks_table[db_id[0]]
            except IndexError:
                continue

            res.append(tpa_lock)
        return res

    @property
    @dump_property(severity=2)
    @_check_types.do
    def cover(self) -> _pjt_cover.PJTCover | None:
        """Return the cover.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_cover.PJTCover`
        """
        db_ids = self._table.db.pjt_covers_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                cover = self._table.db.pjt_covers_table[db_id[0]]
            except IndexError:
                continue

            return cover

    @property
    @dump_property(severity=2)
    @_check_types.do
    def boot(self) -> _pjt_boot.PJTBoot | None:
        """Return the boot.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_boot.PJTBoot`
        """
        db_ids = self._table.db.pjt_boots_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                boot = self._table.db.pjt_boots_table[db_id[0]]
            except IndexError:
                continue

            return boot

    # @property
    # def accessories(self) -> list["_pjt_accessory.PJTAccessory"]:
    #     res = []
    #     db_ids = self._table.db.pjt_accessories_table.select('id',
    #                                                          housing_id=self.db_id)
    #
    #     for db_id in db_ids:
    #         try:
    #             accessory = self._table.db.pjt_accessories_table[db_id]
    #         except IndexError:
    #             continue
    #
    #         res.append(accessory)
    #     return res

    _stored_part: _Union["_housing.Housing", None, DefaultStoredValueType] = DefaultStoredValue

    @property
    @dump_property(severity=2)
    @_check_types.do
    def part(self) -> "_housing.Housing":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_housing.Housing`
        """
        if self._stored_part is DefaultStoredValue:
            part_id = self.part_id

            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.housings_table[part_id]

        if self._stored_part is not None:
            if self._obj is not None:
                self._stored_part.add_object(self._obj())

        return self._stored_part

    @_check_types.do
    def find_child_point_ids(self, parent_ids: list[bytes]) -> list[bytes]:
        """Return the row id of every clone of any point in *parent_ids*.

        A second-or-later wire attached to the same terminal/cavity gets its own
        cloned point (``PJTPoint3D.parent_point_id``); a housing move/rotate has
        to carry those clones along with their parents (see
        ``housing_slots.HousingSlots3D``, which asks once per gesture).

        One batched query for the whole set of ids.

        :param parent_ids: ``pjt_points3d`` row ids of the housing's wire-side points.
        :type parent_ids: list[bytes]
        :returns: The row ids of the clones.
        :rtype: list[bytes]
        """
        if not parent_ids:
            return []

        table = self._table.db.pjt_points3d_table
        placeholders = ','.join('?' * len(parent_ids))

        table.execute(
            f'SELECT id FROM pjt_points3d WHERE parent_point_id IN ({placeholders});',
            parent_ids)

        return [row[0] for row in table.fetchall()]

    @_check_types.do
    def _update_position_pegboard(self, point: _point.Point) -> None:
        """Update the peg-board position.

        Batch-cascades to every cavity's/terminal's ``position_pegboard``
        (plus any clones tracked via ``parent_point_id`` -- e.g. a wire
        attached directly to a terminal's peg-board point) -- mirrors
        :meth:`_update_position3d`, minus the housing-accessory (cover/
        boot/tpa-lock/cpa-lock) groups, since those object types have no
        ``position_pegboard`` of their own (no peg-board presence at
        all). Seal DOES have real peg-board presence (see
        ``objects.objects_pegboard.seal.Seal``), so unlike those it must
        cascade here: the housing's own seal, plus per-cavity either the
        seated terminal's seal (SWS on a terminal) or the cavity's own
        seal (PLUG/dummy-pin on an empty cavity) -- a cavity carries one
        or the other, never both. The Y axis is always honored/stored
        here -- locking Y to 0.0 for a housing (or leaving it free for a
        cavity/terminal/seal) is handled at the object level, not here
        (see ``objects.objects_pegboard.base_pegboard``).

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        delta = point - self._o_position_pegboard
        self._o_position_pegboard = point.copy()

        self._slots_pegboard.move(self, np.array(delta.as_float, dtype=np.float64))

    _o_position_pegboard: _point.Point = None

    @property
    @_check_types.do
    def position_pegboard(self) -> _point.Point:
        """Return the peg-board position.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position_pegboard is DefaultStoredValue:
            point_id = self.position_pegboard_id

            if point_id is None:
                self._stored_position_pegboard = None
            else:
                self._stored_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

                point = self._stored_position_pegboard.point
                point.bind(self._update_position_pegboard)
                self._o_position_pegboard = point.copy()

        if self._stored_position_pegboard is not None:
            if self._obj is not None:
                self._stored_position_pegboard.add_object(self._obj())

            point = self._stored_position_pegboard.point
        else:
            point = None

        return point

    @_check_types.do
    def _update_position3d(self, point: _point.Point) -> None:
        """Update the position 3D.

        Moves every point of the housing (its cavities, accessories, terminals,
        wire-side points and seals, which live in the housing's pooled slots) by
        the same delta, brings the database cache up to date and fires the
        callbacks; see this module's docstring (section 9) and ``housing_slots.HousingSlots3D.move``.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """

        delta = point - self._o_position3d
        self._o_position3d = point.copy()

        self._slots3d.move(self, np.array(delta.as_float, dtype=np.float64))

    _o_position3d: _point.Point = None

    @property
    @_check_types.do
    def position3d(self) -> _point.Point:
        """Return the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position3d is DefaultStoredValue:
            point_id = self.position3d_id

            if point_id is None:
                self._stored_position3d = None
            else:
                self._stored_position3d = self._table.db.pjt_points3d_table[point_id]

                point = self._stored_position3d.point
                point.bind(self._update_position3d)
                self._o_position3d = point.copy()

        if self._stored_position3d is not None:
            if self._obj is not None:
                self._stored_position3d.add_object(self._obj())

            point = self._stored_position3d.point
        else:
            point = None

        return point

    @_check_types.do
    def _update_position2d(self, point: _point.Point) -> None:
        """Update the position 2D.

        Batch-cascades to every cavity's own ``position2d`` and (for a
        cavity with a seated terminal) that terminal's own
        ``position2d`` (name anchor) and ``wire_position2d`` (wire-stub
        attachment point -- see ``PJTTerminal.wire_position2d``'s own
        docstring) -- mirrors :meth:`_update_position3d`/
        :meth:`_update_position_pegboard`'s single vectorized delta +
        one batch DB write, replacing the old per-cavity ``+=`` loop
        (one individual DB write per cavity/terminal per drag frame).
        ``cavity.terminal_position2d`` is just an alias for
        ``cavity.position2d`` (same row -- see ``PJTCavity``), so it
        needs no separate entry here. No ``angle2d`` update for either
        -- a cavity's own name / a terminal's own name-label text must
        always render upright/axis-aligned no matter which way the
        owning housing is rotated, only its anchor position follows the
        rotation, so nothing in this pipeline ever writes a cavity's own
        ``angle2d`` at all. ``pjt_points2d`` stores real
        ``x``/``y``/``z`` columns, one per ``Point`` axis (the schematic
        plane is X/Z, so Y stays 0.0 -- see ``PJTPoint2D.point``), so the
        batch row carries all three.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        delta = point - self._o_position2d
        self._o_position2d = point.copy()

        self._slots_schematic.move(np.array(delta.as_float, dtype=np.float64))

    _o_position2d: _point.Point = None

    @property
    @_check_types.do
    def position2d(self) -> _point.Point:
        """Return the position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_position2d is DefaultStoredValue:
            point_id = self.position2d_id

            if point_id is None:
                self._stored_position2d = None
            else:
                self._stored_position2d = self._table.db.pjt_points2d_table[point_id]

                point = self._stored_position2d.point
                point.bind(self._update_position2d)
                self._o_position2d = point.copy()

        if self._stored_position2d is not None:
            if self._obj is not None:
                self._stored_position2d.add_object(self._obj())

            point = self._stored_position2d.point
        else:
            point = None

        return point

    _o_quat3d: list | None = None
    _o_euler3d: list | None = None

    @_check_types.do
    def _update_angle3d(self, angle: _angle.Angle) -> None:
        """Update the angle 3D.

        Rotates every point of the housing about its position and every angle of its
        cavities, terminals, seals and accessories by the housing's own change of
        rotation; see this module's docstring (section 9) and ``housing_slots.HousingSlots3D.rotate``.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

        if self._o_quat3d is None:
            self._o_quat3d = ast.literal_eval(self._table.select('quat3d', id=self._db_id)[0][0])
            self._o_euler3d = ast.literal_eval(self._table.select('angle3d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(self._o_quat3d, self._o_euler3d)

        new_quat = list(angle.as_quat_float)
        new_euler = list(angle.as_euler_float)
        quat = str(new_quat)
        euler = str(new_euler)

        self._table.update(self._db_id, quat3d=quat, angle3d=euler)

        if 'nan' in euler or 'nan' in quat:
            return

        self._o_quat3d = new_quat
        self._o_euler3d = new_euler

        # Compute the true world-space rotation delta as q_new (x) q_old^-1.
        # Using the Euler-path (angle - o_angle) gives a component-wise
        # difference that is only correct when the non-rotated axes are zero.
        actual_delta_q = angle._q - o_angle._q  # NOQA

        self._slots3d.rotate(
            self, np.array(actual_delta_q.as_float, dtype=np.float64),
            np.array(self.position3d.as_numpy, dtype=np.float64))

        self._populate('angle3d')

    _o_quat_pegboard: list | None = None
    _o_euler_pegboard: list | None = None

    @_check_types.do
    def _update_angle_pegboard(self, angle: _angle.Angle) -> None:
        """Update the peg-board angle.

        Mirrors :meth:`_update_angle3d`'s vectorized batch rotation of
        every cavity/terminal/seal position (plus clones) around the
        housing's own :attr:`position_pegboard`, minus the cover/boot/
        tpa-lock/cpa-lock accessory groups (out of peg-board scope, see
        :meth:`_update_position_pegboard` -- seal DOES cascade here,
        same reasoning) and minus the 3D-mesh OBB-based face-alignment
        refinement used to reorient a cavity within a real 3D part mesh
        -- the peg board has no such mesh geometry, so each cavity's
        accumulated quaternion delta is applied directly
        (``_euler_from_matrix_continuous`` on the raw accumulated
        quaternion, same as ``_update_angle3d``'s own fallback path for
        when no OBB face alignment is available).

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

        if self._o_quat_pegboard is None:
            self._o_quat_pegboard = ast.literal_eval(self._table.select('quat_pegboard', id=self._db_id)[0][0])
            self._o_euler_pegboard = ast.literal_eval(self._table.select('angle_pegboard', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(self._o_quat_pegboard, self._o_euler_pegboard)

        new_quat = list(angle.as_quat_float)
        new_euler = list(angle.as_euler_float)
        quat = str(new_quat)
        euler = str(new_euler)

        self._table.update(self._db_id, quat_pegboard=quat, angle_pegboard=euler)

        if 'nan' in euler or 'nan' in quat:
            return

        self._o_quat_pegboard = new_quat
        self._o_euler_pegboard = new_euler

        actual_delta_q = angle._q - o_angle._q  # NOQA

        self._slots_pegboard.rotate(
            self, np.array(actual_delta_q.as_float, dtype=np.float64),
            np.array(self.position_pegboard.as_numpy, dtype=np.float64))

        self._populate('angle_pegboard')

    _o_quat2d: list | None = None
    _o_euler2d: list | None = None

    @_check_types.do
    def _update_angle2d(self, angle: _angle.Angle) -> None:
        """Update the angle 2D.

        Batch-cascades to every cavity's own ``position2d`` and (for a
        cavity with a seated terminal) that terminal's own
        ``position2d``/``wire_position2d`` -- the schematic rotation
        counterpart to :meth:`_update_position2d` (see its own
        docstring for why ``terminal_position2d`` needs no separate
        entry), rotating each one around the housing's own
        ``position2d`` by the same quaternion-delta vectorized rotation
        :meth:`_update_angle3d`/:meth:`_update_angle_pegboard` use. The
        schematic view only ever rotates about world Y (locked to 90°
        increments -- see ``Angle2DControl._on_angle``), but the
        quaternion-delta rotation is dimension-agnostic, so the same
        formula applies unchanged. No OBB-based re-orientation like
        :meth:`_update_angle3d` -- neither a cavity (no ``Angle2DMixin``
        on ``PJTCavity``) nor a terminal has an ``angle2d`` of its own
        that follows the housing's rotation -- nothing in this pipeline
        ever drives either one's own ``angle2d`` from the housing's,
        just a schematic position that does.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        if self._o_quat2d is None:
            self._o_quat2d = ast.literal_eval(self._table.select('quat2d', id=self._db_id)[0][0])
            self._o_euler2d = ast.literal_eval(self._table.select('angle2d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(self._o_quat2d, self._o_euler2d)

        new_quat = list(angle.as_quat_float)
        new_euler = list(angle.as_euler_float)
        quat = str(new_quat)
        euler = str(new_euler)

        self._table.update(self._db_id, quat2d=quat, angle2d=euler)

        if 'nan' in euler or 'nan' in quat:
            return

        self._o_quat2d = new_quat
        self._o_euler2d = new_euler

        actual_delta_q = angle._q - o_angle._q  # NOQA

        # Exactly 180 degrees is laid out differently from a plain rotation (see
        # CavityGeometry.point_at_180): each stored point gets its own Z correction, taken off before
        # the rotation when it starts from 180 and put on after it when it ends at 180.
        from_180 = bool(_cavity_layout.is_180(o_angle.y))
        to_180 = bool(_cavity_layout.is_180(angle.y))

        self._slots_schematic.rotate(
            self, np.array(actual_delta_q.as_float, dtype=np.float64),
            np.array(self.position2d.as_numpy, dtype=np.float64), from_180, to_180)

        self._populate('angle2d')


class PJTHousingControl(QtWidgets.QTabWidget, LazyTabMixin):
    """Represent a PJT housing control in :mod:`harness_designer.database.project_db.pjt_housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTHousing | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTHousing`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int) -> None:
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible2d_ctrl.set_obj(self.db_obj)
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle2d_ctrl.set_obj(self.db_obj)
            self.angle3d_ctrl.set_obj(self.db_obj)
            self.angle_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position2d_ctrl.set_obj(self.db_obj)
            self.position3d_ctrl.set_obj(self.db_obj)
            self.position_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._cover_page:
            self.cover_ctrl.set_obj(None if self.db_obj is None else self.db_obj.cover)
        elif page is self._boot_page:
            self.boot_ctrl.set_obj(None if self.db_obj is None else self.db_obj.boot)
        elif page is self._cpa_lock_page:
            self.cpa_lock_ctrl.set_obj(None if self.db_obj is None else self.db_obj.cpa_lock)
        elif page is self._tpa_lock1_page:
            self.tpa_lock1_ctrl.set_obj(None if self.db_obj is None else self.db_obj.tpa_lock1)
        elif page is self._tpa_lock2_page:
            self.tpa_lock2_ctrl.set_obj(None if self.db_obj is None else self.db_obj.tpa_lock2)
        elif page is self._seal_page:
            self.seal_ctrl.set_obj(None if self.db_obj is None else self.db_obj.seal)
        elif page is self._cavities_page:
            while self.cavities_notebook.count():
                self.cavities_notebook.removeTab(0)

            self.cavity_pages = {}
            self.cavity_pages_loaded = set()

            if self.db_obj is not None:
                cavities = self.db_obj.cavities
                for cavity in cavities:
                    if cavity is None:
                        continue

                    placeholder = QtWidgets.QWidget()
                    index = self.cavities_notebook.addTab(placeholder, cavity.name)

                    self.cavity_pages[index] = cavity

            if self.cavity_pages:
                index = min(list(self.cavity_pages.keys()))

                self.cavity_pages_loaded.add(index)
                cavity = self.cavity_pages.pop(index)

                widget = _pjt_cavity.PJTCavityControl(self.cavities_notebook)
                widget.set_obj(cavity)
                name = self.cavities_notebook.tabText(index)
                self.cavities_notebook.removeTab(index)
                self.cavities_notebook.insertTab(index, widget, name)
                self.cavities_notebook.setCurrentIndex(index)

        elif page is self._part_page:
            self.part_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    @_check_types.do
    def _on_cavity_tab_changed(self, index: int) -> None:
        if index in self.cavity_pages_loaded or index not in self.cavity_pages:
            return

        self.cavity_pages_loaded.add(index)
        cavity = self.cavity_pages.pop(index)

        widget = _pjt_cavity.PJTCavityControl(self.cavities_notebook)
        widget.set_obj(cavity)
        name = self.cavities_notebook.tabText(index)
        self.cavities_notebook.removeTab(index)
        self.cavities_notebook.insertTab(index, widget, name)
        self.cavities_notebook.setCurrentIndex(index)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`PJTHousingControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTHousing | None = None

        QtWidgets.QTabWidget.__init__(self, parent)
        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.note_ctrl)
        general_page.addWidget(self.smooth_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)
        self.angle_pegboard_ctrl = AnglePegboardControl(angle_page)

        angle_page.addWidget(self.angle2d_ctrl)
        angle_page.addWidget(self.angle3d_ctrl)
        angle_page.addWidget(self.angle_pegboard_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)
        self.position_pegboard_ctrl = PositionPegboardControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)
        position_page.addWidget(self.position_pegboard_ctrl)

        self._cavities_page = cavities_page = _prop_ctrls.Category(self, 'Cavities')
        self.cavities_notebook = QtWidgets.QTabWidget(cavities_page)
        self.cavities_notebook.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.cavities_notebook.setUsesScrollButtons(True)
        self.cavity_pages = {}
        self.cavity_pages_loaded = set()
        self.cavities_notebook.currentChanged.connect(self._on_cavity_tab_changed)

        cavities_page.addWidget(self.cavities_notebook)

        self._cover_page = cover_page = _prop_ctrls.Category(self, 'Cover')
        self.cover_ctrl = _pjt_cover.PJTCoverControl(cover_page)

        cover_page.addWidget(self.cover_ctrl)

        self._boot_page = boot_page = _prop_ctrls.Category(self, 'Boot')
        self.boot_ctrl = _pjt_boot.PJTBootControl(boot_page)

        boot_page.addWidget(self.boot_ctrl)

        self._cpa_lock_page = cpa_lock_page = _prop_ctrls.Category(self, 'CPA Lock')
        self.cpa_lock_ctrl = _pjt_cpa_lock.PJTCPALockControl(cpa_lock_page)

        cpa_lock_page.addWidget(self.cpa_lock_ctrl)

        self._tpa_lock1_page = tpa_lock1_page = _prop_ctrls.Category(self, 'TPA Lock 1')
        self.tpa_lock1_ctrl = _pjt_tpa_lock.PJTTPALockControl(tpa_lock1_page)

        tpa_lock1_page.addWidget(self.tpa_lock1_ctrl)

        self._tpa_lock2_page = tpa_lock2_page = _prop_ctrls.Category(self, 'TPA Lock 2')
        self.tpa_lock2_ctrl = _pjt_tpa_lock.PJTTPALockControl(tpa_lock2_page)

        tpa_lock2_page.addWidget(self.tpa_lock2_ctrl)

        self._seal_page = seal_page = _prop_ctrls.Category(self, 'Seal')
        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        seal_page.addWidget(self.seal_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.part_ctrl = _housing.HousingControl(part_page)

        part_page.addWidget(self.part_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            cover_page,
            boot_page,
            cpa_lock_page,
            tpa_lock1_page,
            tpa_lock2_page,
            seal_page,
            cavities_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
