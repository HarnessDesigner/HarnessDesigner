# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref
from PySide6.QtWidgets import QTabWidget
import build123d

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Angle2DMixin, Angle2DControl,
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NotesMixin, NotesControl
)


if TYPE_CHECKING:
    from ...objects import note as _note_obj


class PJTNotesTable(PJTTableBase):
    """Represent a PJT notes table in :mod:`harness_designer.database.project_db.pjt_note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_notes'

    _control: "PJTNoteControl" = None

    @property
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
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTNoteControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import notes

        return notes.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import notes

        notes.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import notes

        notes.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTNote"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTNote']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTNote(self, db_id, self.project_id)

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
        if isinstance(item, int):
            if item in self:
                return PJTNote(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point2d_id: int | None, point3d_id: int | None,
               note: str, size: int) -> "PJTNote":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param point2d_id: Identifier for the point 2D.
        :type point2d_id: int | None
        :param point3d_id: Identifier for the point 3D.
        :type point3d_id: int | None
        :param note: Value for ``note``.
        :type note: str
        :param size: Value for ``size``.
        :type size: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTNote`
        """

        db_id = PJTTableBase.insert(self, point2d_id=point2d_id,
                                    point3d_id=point3d_id, note=note, size=size)

        return PJTNote(self, db_id, self.project_id)


class PJTNote(PJTEntryBase, Angle3DMixin, Angle2DMixin, NotesMixin,
              Position3DMixin, Position2DMixin, Visible3DMixin, Visible2DMixin):
    """Represent a PJT note in :mod:`harness_designer.database.project_db.pjt_note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTNotesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        packet = {
            'pjt_notes': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id],
        }

        return packet

    def get_object(self) -> "_note_obj.Note":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_note_obj.Note`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

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
    def table(self) -> PJTNotesTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTNotesTable`
        """
        return self._table

    @property
    def size2d(self) -> int:
        """Return the size 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('size2d', id=self._db_id)[0][0]

    @size2d.setter
    def size2d(self, value: int):
        """Set the size 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, size2d=value)
        self._populate('size2d')

    @property
    def h_align2d(self) -> int:
        """Return the h align 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('h_align2d', id=self._db_id)[0][0]

    @h_align2d.setter
    def h_align2d(self, value: int):
        """Set the h align 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, h_align2d=value)
        self._populate('h_align2d')

    @property
    def v_align2d(self) -> int:
        """Return the v align 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('v_align2d', id=self._db_id)[0][0]

    @v_align2d.setter
    def v_align2d(self, value: int):
        """Set the v align 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, v_align2d=value)
        self._populate('v_align2d')

    @property
    def style2d(self) -> int:
        """Return the style 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('style2d', id=self._db_id)[0][0]

    @style2d.setter
    def style2d(self, value: int):
        """Set the style 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, style2d=value)
        self._populate('style2d')

    @property
    def is_visible2d(self) -> bool:
        """Return the is visible 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('is_visible2d', id=self._db_id)[0][0])

    @is_visible2d.setter
    def is_visible2d(self, value: bool):
        """Set the is visible 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_visible2d=int(value))
        self._populate('is_visible2d')

    @property
    def size3d(self) -> float:
        """Return the size 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('size3d', id=self._db_id)[0][0]

    @size3d.setter
    def size3d(self, value: float):
        """Set the size 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, size3d=value)
        self._populate('size3d')

    @property
    def h_align3d(self) -> int:
        """Return the h align 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('h_align3d', id=self._db_id)[0][0]

    @h_align3d.setter
    def h_align3d(self, value: int):
        """Set the h align 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, h_align3d=value)
        self._populate('h_align3d')

    @property
    def v_align3d(self) -> int:
        """Return the v align 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('v_align3d', id=self._db_id)[0][0]

    @v_align3d.setter
    def v_align3d(self, value: int):
        """Set the v align 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, v_align3d=value)
        self._populate('v_align3d')

    @property
    def style3d(self) -> int:
        """Return the style 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('style3d', id=self._db_id)[0][0]

    @style3d.setter
    def style3d(self, value: int):
        """Set the style 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, style3d=value)
        self._populate('style3d')

    @property
    def is_visible3d(self) -> bool:
        """Return the is visible 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('is_visible3d', id=self._db_id)[0][0])

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        """Set the is visible 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_visible3d=int(value))
        self._populate('is_visible3d')


class PJTNoteControl(QTabWidget):
    """Represent a PJT note control in :mod:`harness_designer.database.project_db.pjt_note`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTNote):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTNote`
        """
        if self.db_obj is not None:
            if self.db_obj.is_visible2d:
                self.align_2d_ctrl.SetValue(build123d.TextAlign.LEFT)
                self.style_2d_ctrl.SetValue(build123d.FontStyle.REGULAR)

            if self.db_obj.is_visible3d:
                self.align_3d_ctrl.SetValue(build123d.TextAlign.LEFT)
                self.style_3d_ctrl.SetValue(build123d.FontStyle.REGULAR)

        self.db_obj = db_obj

        self.note_ctrl.set_obj(db_obj)

        self.angle2d_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)

        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)

        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.align_2d_ctrl.Enable(False)
            self.style_2d_ctrl.Enable(False)
            self.align_3d_ctrl.Enable(False)
            self.style_3d_ctrl.Enable(False)
        else:
            if db_obj.is_visible2d:
                self.align_2d_ctrl.SetLabels(['Left', 'Center', 'Right'])
                self.align_2d_ctrl.SetItems(
                    [build123d.TextAlign.LEFT, build123d.TextAlign.CENTER,
                     build123d.TextAlign.RIGHT])

                self.align_2d_ctrl.show()
                self.align_2d_ctrl.SetValue(db_obj.h_align2d)

                self.style_2d_ctrl.SetLabels(['Normal', 'Bold', 'Italic', 'Bold Italic'])
                self.style_2d_ctrl.SetItems(
                    [build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                     build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC])

                self.style_2d_ctrl.show()
                self.style_2d_ctrl.SetValue(db_obj.h_align3d)
            else:
                self.align_2d_ctrl.hide()
                self.style_2d_ctrl.hide()

            if db_obj.is_visible3d:
                self.align_3d_ctrl.SetLabels(['Left', 'Center', 'Right'])
                self.align_3d_ctrl.SetItems(
                    [build123d.TextAlign.LEFT, build123d.TextAlign.CENTER,
                     build123d.TextAlign.RIGHT])

                self.align_3d_ctrl.show()
                self.align_3d_ctrl.SetValue(db_obj.h_align3d)

                self.style_3d_ctrl.SetLabels(['Normal', 'Bold', 'Italic', 'Bold Italic'])
                self.style_3d_ctrl.SetItems(
                    [build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                     build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC])

                self.style_3d_ctrl.show()
                self.style_3d_ctrl.SetValue(db_obj.h_align3d)
            else:
                self.align_3d_ctrl.hide()
                self.style_3d_ctrl.hide()

    def _on_align2d(self, evt):
        """Handle the align 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.h_align2d = value

    def _on_align3d(self, evt):
        """Handle the align 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.h_align3d = value

    def _on_style2d(self, evt):
        """Handle the style 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.style2d = value

    def _on_style3d(self, evt):
        """Handle the style 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.style3d = value

    def __init__(self, parent):
        """Initialise the :class:`PJTNoteControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTNote = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')
        self.note_ctrl = NotesControl(general_page)

        style_page = _prop_ctrls.Category(self, 'Style')
        self.style_2d_ctrl = _prop_ctrls.EnumProperty(style_page, '2D Style')
        self.style_3d_ctrl = _prop_ctrls.EnumProperty(style_page, '3D Style')

        align_page = _prop_ctrls.Category(self, 'Align')
        self.align_2d_ctrl = _prop_ctrls.EnumProperty(align_page, '2D Align')
        self.align_3d_ctrl = _prop_ctrls.EnumProperty(align_page, '3D Align')

        self.style_2d_ctrl.property_changed.connect(self._on_style2d)
        self.style_3d_ctrl.property_changed.connect(self._on_style3d)

        self.align_2d_ctrl.property_changed.connect(self._on_align2d)
        self.align_3d_ctrl.property_changed.connect(self._on_align3d)

        angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            style_page,
            align_page
        ):
            self.addTab(page, page.GetLabel())
            page.Realize()
