# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref
from PySide6.QtWidgets import QTabWidget
import build123d

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Angle3DLockMixin, Angle3DLockControl,
    Angle2DMixin, Angle2DControl,
    AnglePegboardMixin,
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    PositionPegboardMixin,
    Visible2DMixin, Visible2DControl,
    Visible3DMixin, Visible3DControl,
    VisiblePegboardMixin, VisiblePegboardControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl,
    Scale3DMixin, Scale3DControl,
    ColorMixin, ColorControl
)
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...objects import note as _note_obj


class PJTNotesTable(PJTTableBase):
    """Represent a PJT notes table in :mod:`harness_designer.database.project_db.pjt_note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_notes'

    _control: "PJTNoteControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTNoteControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTNoteControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTNoteControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import notes

        return notes.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import notes

        notes.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import notes

        notes.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTNote"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTNote']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTNote(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTNote":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTNote`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTNote or item in self:
                return PJTNote(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(
        self,
        point3d_id: bytes | None, point2d_id: bytes | None,
        point_pegboard_id: bytes | None, notes: str,
        size: int, h_align: int, style: int,
        color_id: bytes | DefaultStoredValueType = DefaultStoredValue) -> "PJTNote":
        """Execute the insert operation.

        A note belongs to exactly one view, never more than one --
        exactly one of point2d_id/point3d_id/point_pegboard_id should
        be given (the caller leaves the other two ``None``), matching
        whichever view actually placed it. Nothing here creates that
        point row lazily (unlike most other placed-object types) --
        the caller is expected to have already created it (e.g. via
        ``pjt_points3d_table.insert(...)`` for a 3D-placed note) and
        pass its id in directly, same as every other reference column
        here. size/h_align/style are each a single value, not a
        separate copy per view -- see :class:`PJTNote`'s own class
        docstring. is_visible2d/is_visible3d/is_visible_pegboard are
        each a real, independent per-view column (see Visible2DMixin/
        Visible3DMixin/VisiblePegboardMixin) -- not passed here, they
        default to visible (1) same as every other object type's own
        insert().

        :param point2d_id: Identifier for the point 2D.
        :type point2d_id: bytes | None
        :param point3d_id: Identifier for the point 3D.
        :type point3d_id: bytes | None
        :param point_pegboard_id: Identifier for the peg-board point.
        :type point_pegboard_id: bytes | None
        :param notes: Value for ``note``.
        :type notes: str
        :param size: Font size.
        :type size: int
        :param h_align: Horizontal text alignment.
        :type h_align: int
        :param style: Font style.
        :type style: int
        :param color_id: Value for ``color_id``.
        :type color_id: bytes
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTNote`
        """
        db_id = PJTTableBase.insert(
            self, point2d_id=point2d_id, point3d_id=point3d_id,
            point_pegboard_id=point_pegboard_id, notes=notes,
            size=size, h_align=h_align, style=style,
            color_id=color_id)

        return PJTNote(self, db_id)


class PJTNote(PJTEntryBase, Angle3DMixin, Angle3DLockMixin, Angle2DMixin, AnglePegboardMixin,
              NotesMixin, ColorMixin,
              Position3DMixin, Position2DMixin, PositionPegboardMixin,
              Visible2DMixin, Visible3DMixin, VisiblePegboardMixin,
              Scale3DMixin, SmoothMixin):
    """Represent a PJT note in :mod:`harness_designer.database.project_db.pjt_note`.

    A note belongs to exactly one view, never more than one -- exactly
    one of point2d_id/point3d_id/point_pegboard_id (see
    position2d_id/position3d_id/position_pegboard_id below) is ever
    set, and that is what determines which view actually renders it,
    not a separate per-view size/style/alignment (see ``size``/
    ``h_align``/``style`` below -- each a single, shared value).
    Visibility, unlike those, IS a real, independent column per view
    (Visible2DMixin/Visible3DMixin/VisiblePegboardMixin, inherited
    unchanged same as every other object type) -- a single shared
    column here previously meant the inert-placeholder construction
    for whichever TWO views a note does NOT belong to (see e.g.
    objects_pegboard/note.py's own __init__) each wrote "not visible"
    into that one shared value, permanently clobbering the visibility
    of the ONE view the note actually does belong to.
    """

    _table: PJTNotesTable = None

    @_check_types.do
    def get_object(self) -> "_note_obj.Note":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_note_obj.Note`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_note_obj.Note"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_note_obj.Note`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    @_check_types.do
    def table(self) -> PJTNotesTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTNotesTable`
        """
        return self._table

    _stored_size: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def size(self) -> int:
        """Return this note's font size -- shared by every view that
        renders it (see PJTNotesTable.insert()'s own docstring).

        :returns: Property value.
        :rtype: int
        """
        if self._stored_size is DefaultStoredValue:
            self._stored_size = self._table.select('size', id=self._db_id)[0][0]

        return self._stored_size

    @size.setter
    @_check_types.do
    def size(self, value: int):
        """Set this note's font size.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_size = value

        self._table.update(self._db_id, size=value)
        self._populate('size')

    _stored_h_align: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def h_align(self) -> int:
        """Return this note's horizontal text alignment -- shared by
        every view that renders it (see PJTNotesTable.insert()'s own
        docstring).

        :returns: Property value.
        :rtype: int
        """
        if self._stored_h_align is DefaultStoredValue:
            self._stored_h_align = self._table.select('h_align', id=self._db_id)[0][0]

        return self._stored_h_align

    @h_align.setter
    @_check_types.do
    def h_align(self, value: int):
        """Set this note's horizontal text alignment.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_h_align = value

        self._table.update(self._db_id, h_align=value)
        self._populate('h_align')

    _stored_style: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def style(self) -> int:
        """Return this note's font style -- shared by every view that
        renders it (see PJTNotesTable.insert()'s own docstring).

        :returns: Property value.
        :rtype: int
        """
        if self._stored_style is DefaultStoredValue:
            self._stored_style = self._table.select('style', id=self._db_id)[0][0]

        return self._stored_style

    @style.setter
    @_check_types.do
    def style(self, value: int):
        """Set this note's font style.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_style = value

        self._table.update(self._db_id, style=value)
        self._populate('style')

    _stored_position2d_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def position2d_id(self) -> bytes | None:
        """Like ``Position2DMixin``'s own version, but never lazily
        creates a point row on read -- this note either belongs to the
        2D view (point2d_id already set) or it doesn't (see the class
        docstring); silently creating one just because something read
        this property would defeat that distinction entirely, unlike
        e.g. a Housing (which always has a real position in every view
        once placed, so lazy-creating there is correct).

        :returns: Property value.
        :rtype: bytes | None
        """
        if self._stored_position2d_id is DefaultStoredValue:
            self._stored_position2d_id = self._table.select('point2d_id', id=self._db_id)[0][0]

        return self._stored_position2d_id

    @position2d_id.setter
    @_check_types.do
    def position2d_id(self, value: bytes | None):
        """Set this note's own point2d_id -- see the getter's docstring.

        :param value: Value to store or process.
        :type value: bytes | None
        """
        self._stored_position2d_id = value
        self._stored_position2d = DefaultStoredValue

        self._table.update(self._db_id, point2d_id=value)
        self._populate('position2d_id')

    _stored_position3d_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def position3d_id(self) -> bytes | None:
        """Like ``Position3DMixin``'s own version, but never lazily
        creates a point row on read -- see :attr:`position2d_id`'s own
        docstring for why.

        :returns: Property value.
        :rtype: bytes | None
        """
        if self._stored_position3d_id is DefaultStoredValue:
            self._stored_position3d_id = self._table.select('point3d_id', id=self._db_id)[0][0]

        return self._stored_position3d_id

    @position3d_id.setter
    @_check_types.do
    def position3d_id(self, value: bytes | None):
        """Set this note's own point3d_id -- see the getter's docstring.

        :param value: Value to store or process.
        :type value: bytes | None
        """
        self._stored_position3d_id = value
        self._stored_position3d = DefaultStoredValue

        self._table.update(self._db_id, point3d_id=value)
        self._populate('position3d_id')

    _stored_position_pegboard_id: bytes | DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def position_pegboard_id(self) -> bytes | None:
        """Like ``PositionPegboardMixin``'s own version, but never
        lazily creates a point row on read -- see :attr:`position2d_id`'s
        own docstring for why.

        :returns: Property value.
        :rtype: bytes | None
        """
        if self._stored_position_pegboard_id is DefaultStoredValue:
            self._stored_position_pegboard_id = self._table.select(
                'point_pegboard_id', id=self._db_id)[0][0]

        return self._stored_position_pegboard_id

    @position_pegboard_id.setter
    @_check_types.do
    def position_pegboard_id(self, value: bytes | None):
        """Set this note's own point_pegboard_id -- see the getter's
        docstring.

        :param value: Value to store or process.
        :type value: bytes | None
        """
        self._stored_position_pegboard_id = value
        self._stored_position_pegboard = DefaultStoredValue

        self._table.update(self._db_id, point_pegboard_id=value)
        self._populate('position_pegboard_id')


class PJTNoteControl(QTabWidget, LazyTabMixin):
    """Represent a PJT note control in :mod:`harness_designer.database.project_db.pjt_note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTNote | None):
        """Set the obj.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTNote`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
            self.color_control.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle2d_ctrl.set_obj(self.db_obj)
            self.angle3d_ctrl.set_obj(self.db_obj)
            self.angle3d_lock_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position2d_ctrl.set_obj(self.db_obj)
            self.position3d_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible2d_ctrl.set_obj(self.db_obj)
            self.visible3d_ctrl.set_obj(self.db_obj)
            self.visible_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._style_page:
            if self.db_obj is None:
                self.style_ctrl.Enable(False)
            else:
                self.style_ctrl.SetLabels(['Normal', 'Bold', 'Italic', 'Bold Italic'])
                self.style_ctrl.SetItems(
                    [build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                     build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC])
                self.style_ctrl.Enable(True)
                self.style_ctrl.SetValue(self.db_obj.style)
        elif page is self._align_page:
            if self.db_obj is None:
                self.align_ctrl.Enable(False)
            else:
                self.align_ctrl.SetLabels(['Left', 'Center', 'Right'])
                self.align_ctrl.SetItems(
                    [build123d.TextAlign.LEFT, build123d.TextAlign.CENTER,
                     build123d.TextAlign.RIGHT])
                self.align_ctrl.Enable(True)
                self.align_ctrl.SetValue(self.db_obj.h_align)
        self._tab_loaded[index] = True

    @_check_types.do
    def _on_align(self, evt):
        """Handle the align event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.h_align = value

    @_check_types.do
    def _on_style(self, evt):
        """Handle the style event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.style = value

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`PJTNoteControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTNote | None = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')
        self.note_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)
        self.color_control = ColorControl(general_page)

        general_page.addWidget(self.note_ctrl)
        general_page.addWidget(self.smooth_ctrl)
        general_page.addWidget(self.color_control)

        self._style_page = style_page = _prop_ctrls.Category(self, 'Style')
        self.style_ctrl = _prop_ctrls.EnumProperty(style_page, 'Style')

        style_page.addWidget(self.style_ctrl)

        self._align_page = align_page = _prop_ctrls.Category(self, 'Align')
        self.align_ctrl = _prop_ctrls.EnumProperty(align_page, 'Align')

        align_page.addWidget(self.align_ctrl)

        self.style_ctrl.propertyChanged.connect(self._on_style)
        self.align_ctrl.propertyChanged.connect(self._on_align)

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)
        self.angle3d_lock_ctrl = Angle3DLockControl(angle_page)

        angle_page.addWidget(self.angle2d_ctrl)
        angle_page.addWidget(self.angle3d_ctrl)
        angle_page.addWidget(self.angle3d_lock_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)
        self.visible_pegboard_ctrl = VisiblePegboardControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)
        visible_page.addWidget(self.visible_pegboard_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            style_page,
            align_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
