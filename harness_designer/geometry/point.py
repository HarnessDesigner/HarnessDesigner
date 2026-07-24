# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Reactive point primitives shared across the geometry subsystem."""

from typing import Self, Iterable, Union

import weakref
import numpy as np

from .decimal import Decimal as _d
from .. import app_mixins as _app_mixins


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


class Point(_app_mixins.CallbackMixin, metaclass=PointMeta):
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
        in-place operators, set_angle), ``_process_callbacks()`` fires every
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
    ``_process_callbacks()`` returns immediately without firing callbacks.  On
    ``__exit__`` the count is decremented; the caller is responsible for
    triggering the update itself after the block if needed.

    Use the context manager whenever you need to set multiple components
    (x, y, z) in a single logical update without firing callbacks for each
    intermediate state::

        with point:
            point.x = new_x
            point.y = new_y
            point.z = new_z
        # callbacks fire here, once, via an explicit setter or _process_callbacks

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

        self._db_id = db_id
        self._root = None      # None  → this instance IS the root
        self._delegators = []  # only populated on the root instance

        if z is None:
            self.is2d = True
            z = 0.0
        else:
            self.is2d = False

        self._data = np.ascontiguousarray(np.array([x, y, z], dtype=np.float32))

        self.__callbacks__ = []
        self.__unbound_callbacks__ = []
        self.__ref_count__ = 0

    @property
    def db_id(self) -> "str | int | None":
        """
        Return the canonical database id for this Point.

        When this Point is attached to a root via :meth:`attach`, returns
        the root's ``_db_id`` directly — one attribute access, no chain
        walk — so every Point in a group always reports the same id as
        the root that owns the live database row.
        """
        if self._root is not None:
            return self._root._db_id
        return self._db_id

    @db_id.setter
    def db_id(self, value: "str | int | None") -> None:
        self._db_id = value

    def __enter__(self):
        if self._root is None:
            self.__ref_count__ += 1
        else:
            self._root.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._root is None:
            self.__ref_count__ -= 1
        else:
            self._root.__exit__(exc_type, exc_val, exc_tb)

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

        if self._root is not None:
            self._root.x = value
            return

        self._data[0] = value
        self._process_callbacks()

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

        if self._root is not None:
            self._root.y = value
            return

        self._data[1] = value
        self._process_callbacks()

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

        if self._root is not None:
            self._root.z = value
            return

        self._data[2] = value
        self._process_callbacks()

    def copy(self) -> "Point":
        """
        Return a new Point with the same coordinates but NO db_id.

        The copy is not registered in the singleton registry and has no
        callbacks.  Use it for temporary geometric calculations where you
        need a snapshot of the current position without creating a shared
        reference.  Never assign a db_id to a copy — use the original
        singleton for anything that needs to participate in the callback chain.
        """

        return Point(*[float(str(item)) for item in self._data.tolist()])

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
            x, y, z = [_d(str(item)) for item in other.tolist()]
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

        if self._root is not None:
            self._root += other
            return self

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 + x2
        self._data[1] = y1 + y2
        self._data[2] = z1 + z2

        self._process_callbacks()

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

        if self._root is not None:
            self._root -= other
            return self

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 - x2
        self._data[1] = y1 - y2
        self._data[2] = z1 - z2

        self._process_callbacks()

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

        if self._root is not None:
            self._root *= other
            return self

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 * x2
        self._data[1] = y1 * y2
        self._data[2] = z1 * z2

        self._process_callbacks()

        return self

    def __mul__(self, other: Union[float, "Point", np.ndarray, _d]) -> "Point":
        """Return a new Point (no db_id) with the component-wise product."""

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 * x2, y1 * y2, z1 * z2)

    def __itruediv__(self, other: Union[float, "Point", np.ndarray, _d]) -> Self:
        """In-place component-wise divide.  Fires callbacks after the operation."""

        if self._root is not None:
            self._root /= other
            return self

        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 / x2
        self._data[1] = y1 / y2
        self._data[2] = z1 / z2

        self._process_callbacks()

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
                angle = _angle.Angle.from_euler(*[float(str(v)) for v in other.tolist()])
            elif other.shape[0] == 4:
                angle = _angle.Angle.from_quat(*[float(str(v)) for v in other.tolist()])
            else:
                raise TypeError
        else:
            angle = other

        p = self.as_numpy
        p @= angle._q  # NOQA

        p = Point(*[float(str(item)) for item in p.tolist()])

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

        if self._root is not None:
            self._root @= other
            return self

        if isinstance(other, np.ndarray):
            if other.shape[0] == 3:
                angle = _angle.Angle.from_euler(*[float(str(v)) for v in other.tolist()])
            elif other.shape[0] == 4:
                angle = _angle.Angle.from_quat(*[float(str(v)) for v in other.tolist()])
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

        self._process_callbacks()

        return self

    def set_angle(self, angle: "_angle.Angle", origin: "Point"):
        """
        Rotate this Point around *origin* by *angle*, in-place.

        Fires callbacks after the operation.  This is the correct way to
        rotate a shared Point about an arbitrary pivot — it handles the
        translate-rotate-translate sequence internally::

            branch_point.set_angle(delta_angle, transition_centre)
        """

        if self._root is not None:
            self._root.set_angle(angle, origin)
            return

        p = self.copy()

        p -= origin
        p @= angle
        p += origin

        x, y, z = p.as_float
        self._data[0] = x
        self._data[1] = y
        self._data[2] = z

        self._process_callbacks()

    def _on_delegate_changed(self, delegate: "Point") -> None:
        # Sync our buffer from the root's buffer (keeps culling pipeline's
        # raw numpy alias current) then fire every callback registered on
        # this Point so all connected 3D objects update their geometry.
        # Called automatically by the root's _process_callbacks whenever the
        # root's coordinates change; the root fires its OWN registered
        # callbacks first, then each delegator receives this call in turn.
        # Result: one mutation anywhere in the chain fires every callback
        # on every point in the chain exactly once.
        np.copyto(self._data, delegate._data)
        self._process_callbacks()

    def attach(self, other: "Point") -> None:
        """
        Attach *other* to this Point as a delegator.

        **``self`` is the parent (root); ``other`` is the child being attached.**

        If ``self`` is itself attached to a root, ``other`` is attached to
        that root instead — one lookup (``self._root``), no loop.

        After this call:

        * Every mutation on ``other`` is forwarded directly to the root —
          O(1), no chain traversal.
        * Whenever the root's coordinates change, two things happen for
          *every* Point in the group (root fires first, then each delegator):

          1. ``_data`` is updated in-place so raw numpy buffer aliases
             (e.g. the culling pipeline's ``numpy_position``) stay current.
          2. ``_process_callbacks()`` fires every callback registered on
             that Point — geometry callbacks, AABB rebuilds, etc.

          One mutation therefore fires every callback on every Point in
          the group exactly once.

        * ``other.db_id`` returns ``root._db_id`` directly (one attribute
          access) so all Points in the group always report the same id.

        **If ``other`` was itself a root with existing delegators**, all of
        those delegators are lifted onto the new root in a single pass so
        the structure stays flat — every non-root Point holds a one-hop
        ``_root`` reference.

        Call ``pjt_point3d.detach()`` on *other*'s DB entry before this
        call so coordinate changes no longer write back to *other*'s
        temporary database row::

            pjt_preview.detach()
            shared_point.attach(pjt_preview.point)
        """
        # Actual root: self if standalone/root, else self._root (one lookup)
        actual_root = self if self._root is None else self._root

        # Guard: other is already part of this chain.
        # Because the structure is always flat, both conditions are O(1):
        #   other is actual_root       → would create a self-reference
        #   other._root is actual_root → other is already a delegator here
        if other is actual_root or other._root is actual_root:
            return

        # If other is already a delegator somewhere, remove it cleanly first
        if other._root is not None:
            old_root = other._root
            old_root.unbind(other._on_delegate_changed)
            old_root._delegators = [r for r in old_root._delegators
                                    if r() is not other]

        # If other was itself a root with delegators, absorb them all into
        # actual_root so the structure stays flat after this call.
        for ref in other._delegators[:]:
            child = ref()
            if child is None:
                continue

            other.unbind(child._on_delegate_changed)
            actual_root.bind(child._on_delegate_changed)
            child._root = actual_root
            actual_root._delegators.append(ref)

        other._delegators.clear()

        # Remove other from the PointMeta singleton registry.  actual_root
        # now owns the canonical entry for this db_id.
        if other._db_id is not None:
            PointMeta._instances.pop(other._db_id, None)

        other._root = actual_root
        np.copyto(other._data, actual_root._data)
        actual_root.bind(other._on_delegate_changed)
        actual_root._delegators.append(weakref.ref(other))

    def detach(self) -> None:
        """
        Sever this Point's delegation and restore it as a standalone root.

        Restores this Point to the PointMeta singleton registry under its
        own ``_db_id`` so that future lookups return this instance rather
        than creating a fresh one.
        """
        if self._root is not None:
            root = self._root
            root.unbind(self._on_delegate_changed)
            root._delegators = [r for r in root._delegators if r() is not self]
            self._root = None
            if self._db_id is not None:
                PointMeta._instances[self._db_id] = weakref.ref(self)

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

        if not isinstance(other, Point):
            return False

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

        x, y, z = [float(str(v)) for v in self._data.tolist()]
        return x, y, z

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

            point.as_numpy[0] = 10.0  # WRONG — bypasses _process_callbacks()

        Always use the x/y/z setters or in-place operators, which call
        ``_process_callbacks()`` after the mutation so that all registered
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

        x, y, z = [float(str(v)) for v in self._data.tolist()]
        return Point(-x, -y, -z)

    @property
    def inverse(self) -> "Point":
        """Return a new Point with all components negated (no db_id, no callbacks)."""

        return -self


ZERO_POINT = Point(0.0, 0.0, 0.0)

from . import angle as _angle  # NOQA
