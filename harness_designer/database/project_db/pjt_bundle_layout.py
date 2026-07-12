# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    Position3DMixin, Position3DControl,
    Visible3DMixin, Visible3DControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl
)


if TYPE_CHECKING:
    from . import pjt_bundle as _pjt_bundle

    from ...objects import bundle_layout as _bundle_layout_obj


class PJTBundleLayoutsTable(PJTTableBase):
    """Represent a PJT bundle layouts table in :mod:`harness_designer.database.project_db.pjt_bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_bundle_layouts'

    _control: "PJTBundleLayoutControl" = None

    @property
    def control(self) -> "PJTBundleLayoutControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayoutControl`
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
        cls._control = PJTBundleLayoutControl(mainframe)
        cls._control.hide()

    def get_from_position3d_id(self, position3d_id) -> "PJTBundleLayout":
        """Return the from position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayout`
        """
        rows = self.select('id', position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import bundle_cover_layouts

        return bundle_cover_layouts.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_cover_layouts

        bundle_cover_layouts.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_cover_layouts

        bundle_cover_layouts.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTBundleLayout"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTBundleLayout']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundleLayout(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBundleLayout":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayout`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTBundleLayout(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, coord_id: int, diameter: float) -> "PJTBundleLayout":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param coord_id: Identifier for the coord.
        :type coord_id: int
        :param diameter: Value for ``diameter``.
        :type diameter: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayout`
        """
        db_id = PJTTableBase.insert(self, coord_id=coord_id, diameter=diameter)

        return PJTBundleLayout(self, db_id, self.project_id)


class PJTBundleLayout(PJTEntryBase, Position3DMixin, Visible3DMixin, NotesMixin, SmoothMixin):
    """Represent a PJT bundle layout in :mod:`harness_designer.database.project_db.pjt_bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTBundleLayoutsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'pjt_bundle_layouts': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }
        return packet

    def get_object(self) -> "_bundle_layout_obj.BundleLayout":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_bundle_layout_obj.BundleLayout`
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

    def set_object(self, obj: "_bundle_layout_obj.BundleLayout"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle_layout_obj.BundleLayout`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def attached_bundles(self) -> list["_pjt_bundle.PJTBundle"]:
        """Return the attached bundles.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_bundle.PJTBundle']
        """
        res = []
        point_id = self.position3d_id
        db_ids = self._table.db.pjt_bundles_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)

        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTBundleLayoutsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayoutsTable`
        """
        return self._table
    
    _stored_diameter: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def diameter(self) -> float:
        """Return the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_diameter is DefaultStoredValue:
            
            self._stored_diameter = self._table.select('diameter', id=self._db_id)[0][0]
            
        return self._stored_diameter

    @diameter.setter
    def diameter(self, value: float):
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_diameter = value
        
        self._table.update(self._db_id, diameter=value)
        self._populate('diameter')


class PJTBundleLayoutControl(QTabWidget, LazyTabMixin):
    """Represent a PJT bundle layout control in :mod:`harness_designer.database.project_db.pjt_bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTBundleLayout):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTBundleLayout`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.notes_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.diameter_ctrl.SetValue('')
            else:
                self.diameter_ctrl.SetValue(str(self.db_obj.diameter))
        elif page is self._visible_page:
            self.visible_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTBundleLayoutControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTBundleLayout = None
        super().__init__(parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')
        self.notes_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        self.diameter_ctrl = _prop_ctrls.StringProperty(general_page, 'Diameter', read_only=True)

        general_page.addWidget(self.notes_ctrl)
        general_page.addWidget(self.smooth_ctrl)
        general_page.addWidget(self.diameter_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible_ctrl)

        for page in (
            general_page,
            visible_page,
            position_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
