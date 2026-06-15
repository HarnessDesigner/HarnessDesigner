# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Reactive point primitives shared across the geometry subsystem."""

from typing import Self, Iterable, Union

import weakref
import numpy as np

from .decimal import Decimal as _d


class PointMeta(type):
    """
    Metaclass that enforces the Point singleton pattern keyed on db_id.

    When a Point is constructed with a db_id, PointMeta checks whether a
    live instance for that id already exists in _instances.  If it does, the
    existing object is returned instead of creating a new one.  If the weakref
    has been collected (the object was garbage-collected since the last lookup)
    the stale entry is cleaned up and a fresh instance is created.

    Points constructed without a db_id (temporary / geometric Points used for
    intermediate calculations) bypass the registry entirely and are always
    new objects.

    WHY THIS MATTERS
    ----------------
    The singleton guarantee is the foundation of the entire object graph.
    Every wire, bundle, splice, transition branch, housing, terminal, layout
    handle, and service loop that shares a position in 3D space does so by
    holding a reference to the *same* Point instance.  There is exactly one
    Python object per database row in pjt_points3d.

    When a property on that Point is mutated (x, y, or z setter, or any
    in-place arithmetic operator), every registered callback fires
    automatically.  Because all connected objects registered their update
    callbacks on the same instance, moving one end of a shared Point moves
    every object that references it — wires stretch, bundles reflow, service
    loops reposition — without any explicit coordination code.

    The weakref storage means that a Point whose db_id has been removed from
    the database and whose last Python reference has been dropped will be
    garbage-collected normally.  The metaclass then cleans the dead weakref
    from _instances on the next lookup for that id.

    CLEANUP RESPONSIBILITY
    ----------------------
    When a database operation reassigns a wire or bundle endpoint to a
    different point_id (e.g. sharing a bundle endpoint Point), the *old*
    point_id row in pjt_points3d may become unreferenced.  The Python
    Point instance for that id will be garbage-collected once all object
    references to it are dropped, but the database row must be explicitly
    deleted — the metaclass does not know about the database.

    Use the transition_handler._delete_point_if_orphaned() utility after any
    operation that reassigns a start_position3d_id or stop_position3d_id
    setter, to check all referencing tables and delete the row if nothing
    holds it anymore.
    """

    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        """
        Remove a collected weak reference from the singleton cache.

        :param ref: Weak reference previously stored in :attr:`_instances`.
        :type ref: :class:`weakref.ReferenceType`
        :returns: ``None``
        :rtype: None
        """

        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, x: float | _d, y: float | _d,
                 z: float | _d | None = None, db_id: int | str | None = None) -> "Point":
        """
        Return a cached or newly created :class:`Point` instance.

        :param x: X coordinate.
        :type x: float | :class:`~harness_designer.geometry.decimal.Decimal`
        :param y: Y coordinate.
        :type y: float | :class:`~harness_designer.geometry.decimal.Decimal`
        :param z: Optional Z coordinate.
        :type z: float | :class:`~harness_designer.geometry.decimal.Decimal` | None
        :param db_id: Optional cache key for singleton reuse.
        :type db_id: int | str | None
        :returns: Shared or new point instance.
        :rtype: :class:`Point`
        """

        if db_id is not None:
            if db_id not in cls._instances:
                instance = super().__call__(x, y, z, db_id)
                cls._instances[db_id] = weakref.ref(instance)

            elif cls._instances[db_id]() is None:
                # Handle edge case where a reference has been removed
                # but the reference object has not yet been removed from
                # the dict. We have to make sure that we delete the key
                # before adding the object again because of the internal
                # mechanics in weakref and not wanting it to remove
                # the newly added reference
                del cls._instances[db_id]
                instance = super().__call__(x, y, z, db_id)
                cls._instances[db_id] = weakref.ref(instance)
            else:
                instance = cls._instances[db_id]()
        else:
            instance = super().__call__(x, y, z, db_id)

        return instance


class Point(metaclass=PointMeta):
    """
    A 3D (or 2D) position that is the connective tissue of the entire
    harness object graph.

    OVERVIEW
    --------
    Point is a reactive, singleton-per-db_id coordinate object.  Its two
    defining characteristics work together to create the data model:

    1.  **Singleton identity** (enforced by PointMeta)
        Every Point with a db_id maps to exactly one Python instance.
        Passing the same db_id to Point() from anywhere in the codebase
        returns the *same object*.  This means that when a wire and a bundle
        share an endpoint, they literally hold a reference to the same Point
        instance in memory — not two separate objects that happen to have
        equal coordinates.

    2.  **Reactive callbacks**
        Any object that needs to respond to position changes calls
        ``point.bind(self.update_method)`` to register a callback.  Whenever
        any coordinate component is mutated through the Point API (setters,
        in-place operators, set_angle), ``_process_update()`` fires every
        registered callback.  Because all connected objects share the same
        instance, a single mutation propagates to all of them automatically.

    HOW SHARING WORKS IN PRACTICE
    ------------------------------
    Shared endpoints are created entirely through the database layer.  When
    two DB rows (say a wire segment and a bundle section) store the *same*
    integer in their ``start_point3d_id`` / ``stop_point3d_id`` columns,
    the ORM mixin (``StartStopPosition3DMixin.start_position3d``) fetches
    ``pjt_points3d_table[point_id]``, which constructs
    ``Point(x, y, z, db_id=point_id)``.  The metaclass returns the existing
    instance if one is live, or creates a new one if not.  The result is that
    every object whose DB row references that point_id ends up holding a
    reference to the same Python object.

    Examples of shared Points in the project:

    * Wire segments split by a splice: the splice start and stop Points ARE
      the boundary points of the two wire segments.  Moving the splice moves
      those Points, which reflows both segments.

    * A bundle chain connected by layouts: adjacent sections share the layout
      Point as their boundary.  Moving the layout handle moves both sections.

    * A wire routed through a transition: the invisible wire segment inside
      the transition shares the branch position Points with the transition
      branches.  Moving the transition moves the branch Points and therefore
      the wire segment endpoints.

    * A wire entering a bundle: after a drag-and-drop reassignment, the
      wire's endpoint point_id is updated to match the bundle's endpoint
      point_id.  From that moment on they share the same Point instance.

    CONTEXT MANAGER — BATCHING UPDATES
    -----------------------------------
    ``with point:`` increments ``_ref_count``.  While ``_ref_count > 0``
    ``_process_update()`` returns immediately without firing callbacks.  On
    ``__exit__`` the count is decremented; the caller is responsible for
    triggering the update itself after the block if needed.

    Use the context manager whenever you need to set multiple components
    (x, y, z) in a single logical update without firing callbacks for each
    intermediate state::

        with point:
            point.x = new_x
            point.y = new_y
            point.z = new_z
        # callbacks fire here, once, via an explicit setter or _process_update

    CLEANUP — ORPHANED POINT ROWS
    ------------------------------
    When a DB operation reassigns a ``start_position3d_id`` or
    ``stop_position3d_id`` to a different point_id (e.g. sharing a bundle or
    transition branch Point), the *original* point_id row in pjt_points3d
    may no longer be referenced by any other row in any project table.

    The Python instance for the old point_id will be garbage-collected once
    all object references are dropped (the metaclass weakref handles this
    automatically).  But the database row will NOT be deleted automatically.

    Orphan deletion is intentionally deferred rather than done inline after
    every operation.  Inline deletion would mean querying every reference
    column in every project table on every drag-and-drop — expensive and
    unnecessary.  A point that appears temporarily unreferenced between two
    related operations should not be deleted prematurely.

    Cleanup runs in two situations:

    1. **Application exit** — ``MainFrame.on_close`` calls
       ``cleanup_orphaned_points(ptables)`` before closing the database
       connection.  The user never sees this.

    2. **On user request** — exposed via the Tools menu so the user can
       reclaim space or verify database integrity during a session without
       needing to restart.

    The cleanup implementation lives in
    ``database/project_db/cleanup.py``.  It scans every row in
    ``pjt_points3d`` and ``pjt_points2d`` using EXISTS subqueries across
    all reference tables, collecting orphan IDs, then deletes them in a
    single batch DELETE.

    What IS done inline during drag-and-drop is **repointing** — updating
    every object that still references the old Point ID to reference the new
    shared Point instead.  This must happen immediately so the object graph
    stays consistent within the current editing session::

        from handlers.transition_handler import _repoint_all_references
        _repoint_all_references(ptables, old_id, new_id)

    NUMPY INTEROPERABILITY
    ----------------------
    ``_data`` is a contiguous float64 numpy array ``[x, y, z]``.  All
    arithmetic uses Decimal for the computation to avoid floating-point
    accumulation errors, then stores the result back into ``_data``.

    ``__array_ufunc__`` is implemented so that numpy ufuncs (matmul, add,
    subtract, multiply) can accept a Point as either operand, enabling code
    like ``matrix @ point`` or ``array + point`` to work naturally without
    explicit conversion.  The result in those cases is a raw numpy array,
    not a new Point — the Point stays on the right side of the expression
    as the operand, not the result container.
    """

    def __array_ufunc__(self, func, _, inputs, instance, out=None, **__):
        """
        Handle selected NumPy ufuncs involving a point.

        :param func: NumPy ufunc being dispatched.
        :type func: object
        :param method: Ufunc method name.
        :type method: str
        :param inputs: Left-hand input provided by NumPy.
        :type inputs: :class:`numpy.ndarray` | None
        :param instance: Operand instance chosen by NumPy.
        :type instance: :class:`numpy.ndarray` | None
        :param out: Optional output container supplied by NumPy.
        :type out: tuple[:class:`numpy.ndarray`] | None
        :returns: NumPy result for the supported operation.
        :rtype: :class:`numpy.ndarray`
        :raises RuntimeError: If the ufunc is unsupported for :class:`Point`.
        """

        if func == np.matmul:
            # numpy array is left hand and class instance is right hand
            # there would be no case where we would use
            # array @ point
            # or
            # array @= point
            # but for hoots and ha ha's I added support for it.
            if isinstance(instance, Point):
                if out is None:
                    return inputs @ self._data
                else:
                    out = out[0]
                    shape = out.shape

                    if len(shape) == 1:
                        out = out.reshape(-1, 3)

                    out @= self._data

                    if len(shape) == 1:
                        out = out.reshape(-1)

                    return out

            # class instance is left hand and numpy array is right hand
            # this should not happen because of __imatmul__ and __matmul__
            # being available
            # elif isinstance(instance, np.ndarray):
            else:
                raise RuntimeError('sanity check')

        if func == np.add:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Point):
                if out is None:
                    return inputs + self._data
                else:
                    out = out[0]
                    shape = out.shape

                    if len(shape) == 1:
                        out = out.reshape(-1, 3)

                    out += self._data

                    if len(shape) == 1:
                        out = out.reshape(-1)

                    return out

            # class instance is left hand and numpy array is right hand
            # this should not happen because of __iadd__ and __add__
            # being available
            # elif isinstance(instance, np.ndarray):
            else:
                raise RuntimeError('sanity check')

        if func == np.subtract:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Point):
                if out is None:
                    return inputs - self._data
                else:
                    out = out[0]
                    shape = out.shape

                    if len(shape) == 1:
                        out = out.reshape(-1, 3)

                    out -= self._data

                    if len(shape) == 1:
                        out = out.reshape(-1)

                    return out

            # class instance is left hand and numpy array is right hand
            # this should not happen because of __isub__ and __sub__
            # being available
            # elif isinstance(instance, np.ndarray):
            else:
                raise RuntimeError('sanity check')

        if func == np.multiply:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Point):
                if out is None:
                    return inputs * self._data
                else:
                    out = out[0]
                    shape = out.shape

                    if len(shape) == 1:
                        out = out.reshape(-1, 3)

                    out *= self._data

                    if len(shape) == 1:
                        out = out.reshape(-1)

                    return out

            # class instance is left hand and numpy array is right hand
            # this should not happen because of __imul__ and __mul__
            # being available
            # elif isinstance(instance, np.ndarray):
            else:
                raise RuntimeError('sanity check')

        raise RuntimeError

    def __init__(self, x: float | _d, y: float | _d,
                 z: float | _d | None = None, db_id: int | str | None = None):
        """
        Construct a Point.

        Parameters
        ----------
        x, y : float | Decimal
            Coordinate values.
        z : float | Decimal | None
            When None the Point is treated as 2D (is2d=True) and z is
            stored as 0.0 internally.  Passing a value makes it 3D.
        db_id : int | str | None
            When provided, PointMeta uses this as the singleton key.
            Two calls with the same db_id return the same instance.

            The db_id format used throughout the project is a string like
            ``"1233d"`` (3D point) or ``"1232d"`` (2D point), where the
            integer part is the row id in pjt_points3d or pjt_points2d.
            Stripping the suffix with ``int(db_id[:-2])`` gives the raw
            database integer used in insert / update calls.

            Pass None for temporary Points used in geometry calculations
            that have no database backing and should never be shared.
        """

        self.db_id = db_id

        if z is None:
            self.is2d = True
            z = 0.0
        else:
            self.is2d = False

        self._data = np.ascontiguousarray(np.array([x, y, z], dtype=np.float32))

        self._callbacks = []
        self._unbound_callbacks = []
        self._ref_count = 0

    def __enter__(self):
        """
        Begin a batched update.

        Increments the internal ref-count guard so that individual x, y, z
        setter calls and in-place operators do NOT fire callbacks while the
        context is active.  This lets you update all three components as a
        single logical move without triggering intermediate redraws or
        geometry recalculations::

            with point:
                point.x = 10.0
                point.y = 20.0
                point.z =  5.0
            # no callbacks fired during the block

        The caller must trigger ``_process_update()`` explicitly after the
        block if the change should propagate, OR use a final setter outside
        the block which will fire ``_process_update()`` normally.

        Note: the context manager does NOT automatically fire callbacks on
        exit.  This is intentional — some callers (e.g. the transition 3D
        object's __init__) need to update points without triggering redraws
        until the entire object is ready.
        """

        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Decrement the ref-count guard.  See __enter__."""

        self._ref_count -= 1

    def __remove_callback(self, ref):
        """
        Drop a dead callback weak reference from the callback list.

        :param ref: Weak method reference scheduled for removal.
        :type ref: :class:`weakref.WeakMethod`
        :returns: ``None``
        :rtype: None
        """

        try:
            self._callbacks.remove(ref)
        except:  # NOQA
            pass

    def bind(self, callback):
        """
        Register a callback to be called whenever this Point's coordinates
        change.

        The callback receives the Point instance as its only argument.
        Internally it is stored as a ``WeakMethod`` so that binding a bound
        method does not prevent the owning object from being garbage-collected.
        When the owning object is collected the dead weakref is silently
        removed from the callback list during the next ``_process_update()``.

        Duplicate registrations are tolerated — the first duplicate found
        during ``_process_update()`` is removed so each unique callback fires
        at most once per update cycle.

        IMPORTANT — objects must bind their callbacks at the same time they
        acquire a reference to the Point (i.e. in the ORM mixin property
        accessor after calling ``add_object``).  If a callback is never bound,
        the object will not respond to position changes even though it holds a
        reference to the shared Point.
        """

        # we don't explicitly check to see if a callback is already registered
        # what we care about is if a callback is called only one time and that
        # check is done when the callbacks are being done and if there happend
        # to be a duplicate the duplicate is then removed at that point in time.
        ref = weakref.WeakMethod(callback, self.__remove_callback)

        self._callbacks.append(ref)

    def unbind(self, callback):
        """
        Remove a previously registered callback.

        Iterates the full callback list removing ALL registrations of the
        given callback, including any duplicates.  This is intentional: if a
        callback was accidentally bound more than once, a single unbind call
        removes all copies.

        IMPORTANT — when an object is deleted or its connection to this Point
        is severed (e.g. a wire endpoint is reassigned to a different point_id),
        unbind should be called to avoid the callback firing for a Point the
        object no longer owns.  Failure to unbind is not fatal — the WeakMethod
        will eventually be collected — but it can cause spurious updates while
        the owning object still exists.
        """

        ref = weakref.WeakMethod(callback)
        if ref in self._callbacks:
            while ref in self._callbacks:
                self._callbacks.remove(ref)
        else:
            self._unbound_callbacks.append(callback)

        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                while ref in self._callbacks:
                    self._callbacks.remove(ref)

    def _process_update(self):
        """
        Fire all registered callbacks, unless batching is active.

        Called automatically by every coordinate mutation (x/y/z setters,
        __iadd__, __isub__, __imul__, __itruediv__, __imatmul__, set_angle).

        If ``_ref_count`` is non-zero (i.e. the caller is inside a ``with
        point:`` block) this method returns immediately without firing
        anything.  This is the mechanism that allows multiple coordinate
        components to be updated atomically.

        Dead weakrefs (callbacks whose owning object has been collected) are
        silently pruned during iteration.  Duplicate callbacks are detected
        and removed — each unique callback fires at most once per update cycle
        even if it was registered more than once.
        """

        if self._ref_count:
            return

        del self._unbound_callbacks[:]
        used_callbacks = []
        callbacks = self._callbacks[:]
        del self._callbacks[:]

        for ref in callbacks:
            if ref in used_callbacks:
                continue
            cb = ref()
            if cb is None:
                continue
            cb(self)
            used_callbacks.append(ref)

        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
            elif cb in self._unbound_callbacks:
                self._unbound_callbacks.remove(cb)

        self._callbacks.extend([
            ref for ref in used_callbacks
            if ref() is not None
            and ref not in self._callbacks
            and ref() not in self._unbound_callbacks
        ])

        del self._unbound_callbacks[:]

    @property
    def x(self) -> _d:
        """
        Return the X coordinate.

        :returns: Current X component.
        :rtype: :class:`~harness_designer.geometry.decimal.Decimal`
        """

        return _d(self._data[0])

    @x.setter
    def x(self, value: float | _d):
        """
        Set the X component

        Fires callbacks (unless batching).
        """

        self._data[0] = value
        self._process_update()

    @property
    def y(self) -> _d:
        """
        Return the Y coordinate.

        :returns: Current Y component.
        :rtype: :class:`~harness_designer.geometry.decimal.Decimal`
        """

        return _d(self._data[1])

    @y.setter
    def y(self, value: float | _d):
        """
        Set the Y component

        Fires callbacks (unless batching).
        """

        self._data[1] = value
        self._process_update()

    @property
    def z(self) -> _d:
        """
        Return the Z coordinate.

        :returns: Current Z component.
        :rtype: :class:`~harness_designer.geometry.decimal.Decimal`
        """

        return _d(self._data[2])

    @z.setter
    def z(self, value: float | _d):
        """
        Set the Z component

        Fires callbacks (unless batching).
        """

        self._data[2] = value
        self._process_update()

    def copy(self) -> "Point":
        """
        Return a new Point with the same coordinates but NO db_id.

        The copy is not registered in the singleton registry and has no
        callbacks.  Use it for temporary geometric calculations where you
        need a snapshot of the current position without creating a shared
        reference.  Never assign a db_id to a copy — use the original
        singleton for anything that needs to participate in the callback chain.
        """

        return Point(*self._data.tolist())

    @staticmethod
    def __other_to_decimal(other: Union[_d, float, "Point", np.ndarray]) -> tuple[_d, _d, _d]:
        """
        Convert supported operand types to decimal coordinate triples.

        :param other: Operand to normalize.
        :type other: :class:`~harness_designer.geometry.decimal.Decimal` | float | :class:`Point` | :class:`numpy.ndarray`
        :returns: Decimal ``(x, y, z)`` components.
        :rtype: tuple[:class:`~harness_designer.geometry.decimal.Decimal`, :class:`~harness_designer.geometry.decimal.Decimal`, :class:`~harness_designer.geometry.decimal.Decimal`]
        :raises TypeError: If ``other`` cannot be converted.
        """

        if isinstance(other, np.ndarray):
            x, y, z = [_d(item) for item in other.tolist()]
        elif isinstance(other, Point):
            x, y, z = other.as_decimal
        elif isinstance(other, float):
            x = y = z = _d(other)
        elif isinstance(other, _d):
            x = y = z = other
        else:
            raise TypeError(f'incorrect type "{type(other)}"')

        return x, y, z

    def __iadd__(self, other: Union["Point", np.ndarray, float]) -> Self:
        """
        In-place add.

        Fires callbacks after the operation unless batching.

        This is the primary way to move a shared Point — every object that
        has bound a callback (wires, bundles, layouts, etc.) will receive the
        update and recompute their geometry::

            # Move a wire endpoint and everything connected to it
            position += delta
        """

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 + x2
        self._data[1] = y1 + y2
        self._data[2] = z1 + z2

        self._process_update()

        return self

    def __add__(self, other: Union["Point", np.ndarray, float, _d]) -> "Point":
        """
        Return a new Point (no db_id, no callbacks) with the summed
        coordinates.

        Does NOT fire callbacks on self.  Use __iadd__ when
        you intend to move a shared Point.
        """

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 + x2, y1 + y2, z1 + z2)

    def __isub__(self, other: Union["Point", np.ndarray, float, _d]) -> Self:
        """
        In-place subtract.

        Fires callbacks after the operation.
        """

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 - x2
        self._data[1] = y1 - y2
        self._data[2] = z1 - z2

        self._process_update()

        return self

    def __sub__(self, other: Union["Point", np.ndarray, float, _d]) -> "Point":
        """Return a new Point (no db_id, no callbacks) with the difference."""

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 - x2, y1 - y2, z1 - z2)

    def __imul__(self, other: Union[float, "Point", np.ndarray, _d]) -> Self:
        """
        In-place component-wise multiply.

        Fires callbacks after the operation.

        Primarily used for scaling — e.g. multiplying a unit-space VBO
        endpoint by a scale Point to get world-space coordinates::

            stop_local *= scale  # scale is Point(diameter, diameter, diameter)
        """

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 * x2
        self._data[1] = y1 * y2
        self._data[2] = z1 * z2

        self._process_update()

        return self

    def __mul__(self, other: Union[float, "Point", np.ndarray, _d]) -> "Point":
        """Return a new Point (no db_id) with the component-wise product."""

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 * x2, y1 * y2, z1 * z2)

    def __itruediv__(self, other: Union[float, "Point", np.ndarray, _d]) -> Self:
        """In-place component-wise divide.  Fires callbacks after the operation."""

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 / x2
        self._data[1] = y1 / y2
        self._data[2] = z1 / z2

        self._process_update()

        return self

    def __truediv__(self, other: Union[_d, float, "Point", np.ndarray]) -> "Point":
        """Return a new Point (no db_id) with the component-wise quotient."""

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 / x2, y1 / y2, z1 / z2)

    def __matmul__(self, other: Union[np.ndarray, "_angle.Angle"]) -> "Point":
        """
        Return a new Point (no db_id) rotated by *other*.

        *other* can be an Angle instance, a 3-element euler array, or a
        4-element quaternion array.  The rotation is applied to ``_data``
        directly via the quaternion representation for speed.

        Does NOT fire callbacks — use __imatmul__ to rotate a shared Point
        in-place and propagate the change to all connected objects.
        """

        if isinstance(other, np.ndarray):
            if other.shape[0] == 3:
                angle = _angle.Angle.from_euler(*other.tolist())
            elif other.shape[0] == 4:
                angle = _angle.Angle.from_quat(*other.tolist())
            else:
                raise TypeError
        else:
            angle = other

        p = self.as_numpy
        p @= angle._q  # NOQA

        p = Point(*p.tolist())

        return p

    def __imatmul__(self, other: Union[np.ndarray, "_angle.Angle"]) -> "Point":
        """
        In-place rotation by *other*.

        Fires callbacks after the operation.

        Used to rotate a shared Point (and propagate the change to all
        connected objects) when the owning object's angle changes::

            # Rotate a branch position when the transition is rotated
            with branch_point:
                branch_point -= transition_centre
                branch_point @= angle_delta
            branch_point += transition_centre
            # callback fires on the += which is outside the with block
        """

        if isinstance(other, np.ndarray):
            if other.shape[0] == 3:
                angle = _angle.Angle.from_euler(*other.tolist())
            elif other.shape[0] == 4:
                angle = _angle.Angle.from_quat(*other.tolist())
            else:
                raise TypeError
        elif isinstance(other, _angle.Angle):
            angle = other

        else:
            raise RuntimeError

        p = self.as_numpy
        p @= angle._q  # NOQA

        self._data[0] = p[0]
        self._data[1] = p[1]
        self._data[2] = p[2]

        self._process_update()

        return self

    def set_angle(self, angle: "_angle.Angle", origin: "Point"):
        """
        Rotate this Point around *origin* by *angle*, in-place.

        Fires callbacks after the operation.  This is the correct way to
        rotate a shared Point about an arbitrary pivot — it handles the
        translate-rotate-translate sequence internally::

            branch_point.set_angle(delta_angle, transition_centre)
        """

        p = self.copy()

        p -= origin
        p @= angle
        p += origin

        x, y, z = p.as_float
        self._data[0] = x
        self._data[1] = y
        self._data[2] = z

        self._process_update()

    def get_angle(self, origin: "Point") -> "_angle.Angle":
        """Return the Angle from *origin* to this Point."""

        return _angle.Angle.from_points(origin, self)

    def __bool__(self):
        """
        False when all three components are effectively zero (within numpy
        isclose tolerance).

        Used to distinguish uninitialized Points
        (e.g. branch positions that have not yet been computed by _build_model)
        from genuine zero-coordinates.
        """

        arr = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        return not all(np.isclose(self._data, arr))

    def __eq__(self, other: "Point") -> bool:
        """Return whether this point matches ``other`` component-wise.

        :param other: Point to compare against.
        :type other: :class:`Point`
        :returns: ``True`` when all coordinates are numerically close.
        :rtype: bool
        """

        return all(np.isclose(self._data, other.as_numpy))

    def __ne__(self, other: "Point") -> bool:
        """Return whether this point differs from ``other``.

        :param other: Point to compare against.
        :type other: :class:`Point`
        :returns: ``True`` when any coordinate differs.
        :rtype: bool
        """

        return not self.__eq__(other)

    @property
    def as_decimal(self):
        """Return (x, y, z) as a tuple of Decimal values for precision arithmetic."""

        x, y, z = self.as_float
        return _d(x), _d(y), _d(z)

    @property
    def as_float(self) -> tuple[float, float, float]:
        """Return (x, y, z) as plain Python floats."""

        x, y, z = self._data.tolist()
        return float(x), float(y), float(z)

    @property
    def as_int(self) -> tuple[int, int, int]:
        """Return (x, y, z) truncated to integers."""

        x, y, z = self.as_float
        return int(x), int(y), int(z)

    @property
    def as_numpy(self) -> np.ndarray:
        """
        Return the underlying float64 numpy array directly — not a copy.

        This property is central to how the 3D culling pipeline stays current
        without any explicit synchronisation.

        HOW IT FITS INTO THE CULLING PIPELINE
        ---------------------------------------
        When a 3D object is registered with the canvas, ``Base3D.__init__``
        does::

            self.numpy_position = self._position.as_numpy

        This stores a direct reference to the Point's own ``_data`` buffer.
        The canvas then builds a culling row::

            [aabb_min, aabb_max, pos, is_opaque, obj_address]

        where ``pos`` is that same ``numpy_position`` reference — the same
        C-contiguous float64 array that lives inside the Point.

        When the Point's position changes (via ``_update_position``)::

            self.numpy_position[:] = position.as_numpy

        the write goes *in-place* into the existing buffer.  The culling row
        already holds a reference to that buffer, so the Cython culling code
        sees the updated position the next time it reads from that pointer —
        with no row rebuild, no re-registration, no copying.

        THE GIL-BOUNDARY TRICK
        -----------------------
        The culling code runs ``with nogil:`` so Python objects cannot cross
        the GIL boundary.  The position data gets through because it is a raw
        C pointer to a numpy buffer — not a Python object.

        The scene object itself is carried across the boundary using a
        different mechanism::

            obj_ref     = weakref.ref(obj, self.__remove_obj_ref)
            obj_address = id(obj_ref)           # integer — crosses GIL freely
            row.append(obj_address)

        ``id()`` returns the memory address of the weakref object as a plain
        Python integer.  On the back side, after the nogil block completes,
        the canvas reconstructs the weakref::

            obj_ref = ctypes.cast(ref_address, ctypes.py_object).value
            obj     = obj_ref()

        If the object was collected while the culling thread was running,
        ``obj_ref()`` returns ``None`` and the row is silently skipped.  This
        is rock-solid safe: the weakref's own finaliser has already been called
        by CPython's reference counting, so the memory address is still valid
        (the weakref object is kept alive by ``self._object_refs``), and
        calling a dead weakref is always safe — it just returns None.

        WHY as_numpy MUST NOT RETURN A COPY
        -------------------------------------
        If ``as_numpy`` returned ``self._data.copy()``, the culling row would
        hold a snapshot that goes stale the moment the Point moves.  Returning
        ``self._data`` directly means every in-place write to the Point
        propagates to the culling buffer automatically, with no extra work.

        IMPORTANT — never mutate the returned array directly::

            point.as_numpy[0] = 10.0  # WRONG — bypasses _process_update()

        Always use the x/y/z setters or in-place operators, which call
        ``_process_update()`` after the mutation so that all registered
        callbacks (geometry recalculation, AABB rebuild, etc.) fire correctly.
        """
        return self._data

    def __iter__(self) -> Iterable[float]:
        """
        Iterate over the point coordinates as floats.

        :returns: Iterator yielding ``x``, ``y``, and ``z``.
        :rtype: collections.abc.Iterable[float]
        """

        return iter(self.as_float)

    def __str__(self) -> str:
        """
        Return a readable coordinate string.

        :returns: String representation of the point.
        :rtype: str
        """

        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'

    def __le__(self, other: "Point") -> bool:
        """
        Return whether every component is less than or equal to ``other``.

        :param other: Point to compare against.
        :type other: :class:`Point`
        :returns: ``True`` when all components are less than or equal.
        :rtype: bool
        """

        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 <= x2 and y1 <= y2 and z1 <= z2

    def __ge__(self, other: "Point") -> bool:
        """
        Return whether every component is greater than or equal to ``other``.

        :param other: Point to compare against.
        :type other: :class:`Point`
        :returns: ``True`` when all components are greater than or equal.
        :rtype: bool
        """

        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 >= x2 and y1 >= y2 and z1 >= z2

    def __neg__(self) -> "Point":
        """
        Return a new point with all coordinates negated.

        :returns: Negated point copy.
        :rtype: :class:`Point`
        """

        x, y, z = self._data.tolist()
        return Point(-x, -y, -z)

    @property
    def inverse(self) -> "Point":
        """Return a new Point with all components negated (no db_id, no callbacks)."""

        return -self


ZERO_POINT = Point(0.0, 0.0, 0.0)

from . import angle as _angle  # NOQA
