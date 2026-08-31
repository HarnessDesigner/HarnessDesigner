# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from .... import check_types as _check_types


class Angle3DLockMixin(BaseMixin):
    """Whether an object's own ``angle3d`` is user-locked rather than
    live-computed.

    Currently only meaningful for :class:`~....database.project_db.
    pjt_note.PJTNote` -- an unlocked note continuously re-faces the 3D
    camera (see ``objects.objects_3d.note``'s own camera-follow batch
    update), while a locked one keeps whatever angle it was locked at,
    same as any ordinary rotatable object. Stored as a plain int column
    (0/1), exposed as a real bool here -- see :class:`Visible3DMixin`
    for the identical shape this mirrors.
    """

    _stored_angle3d_lock: bool | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def angle3d_lock(self) -> bool:
        """Return whether this object's own ``angle3d`` is locked.

        :returns: Property value.
        :rtype: bool
        """
        if self._stored_angle3d_lock is DefaultStoredValue:
            self._stored_angle3d_lock = bool(self._table.select('angle3d_lock', id=self._db_id)[0][0])

        return self._stored_angle3d_lock

    @angle3d_lock.setter
    @_check_types.do
    def angle3d_lock(self, value: bool):
        """Set whether this object's own ``angle3d`` is locked.

        :param value: Value to store or process.
        :type value: bool
        """
        self._stored_angle3d_lock = value

        self._table.update(self._db_id, angle3d_lock=int(value))
        self._populate('angle3d_lock')


class Angle3DLockControl(_prop_ctrls.BoolProperty):
    """Checkbox for :attr:`Angle3DLockMixin.angle3d_lock`.

    Checking it freezes the object's current (possibly still camera-
    following) angle as its new locked value -- see
    ``objects.objects_3d.note.Note.lock_angle``, not just a blind flag
    flip, since a still-tracking note's own ``angle3d`` column can be
    stale (every camera-follow update while unlocked lands on the
    object's own live ``Text``, never on the DB row -- see
    ``shapes.text.Text.enable_camera_tracking``'s own docstring).
    Delegates to the real object (via ``db_obj.get_object()``) rather
    than writing ``angle3d_lock`` directly -- the freeze/resume-tracking
    behavior lives on the object/rendering layer, not here.
    """

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`Angle3DLockControl` instance.

        :param parent: Parent widget.
        :type parent: UNKNOWN
        """
        self.db_obj: Angle3DLockMixin | None = None

        super().__init__(parent, 'Lock Angle')

        self.propertyChanged.connect(self._on_lock_changed)

    @_check_types.do
    def _on_lock_changed(self, evt):
        """Handle the lock-checkbox event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()

        obj = self.db_obj.get_object() if hasattr(self.db_obj, 'get_object') else None
        if obj is not None and hasattr(obj, 'lock_angle') and hasattr(obj, 'unlock_angle'):
            if value:
                obj.lock_angle()
            else:
                obj.unlock_angle()
        else:
            # No live object to delegate to (or a future db_obj type
            # that never grew lock_angle/unlock_angle) -- fall back to
            # the plain flag so the checkbox still does *something*
            # sensible.
            self.db_obj.angle3d_lock = value

    @_check_types.do
    def set_obj(self, db_obj: Angle3DLockMixin | None):
        """Set the obj.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Angle3DLockMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue(False)
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.angle3d_lock)
            self.setEnabled(True)
