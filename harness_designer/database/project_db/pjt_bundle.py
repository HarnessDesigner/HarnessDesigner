# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable, Union

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import bundle_cover as _bundle_cover
from ...geometry import line as _line
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    PartMixin,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl
)


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_bundle_layout as _pjt_bundle_layout
    from . import pjt_wire as _pjt_wire

    from ...objects import bundle as _bundle_obj


class PJTBundlesTable(PJTTableBase):
    """Represent a PJT bundles table in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_bundles'

    _control: "PJTBundleControl" = None

    @property
    def control(self) -> "PJTBundleControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleControl`
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
        cls._control = PJTBundleControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import bundle_covers

        return bundle_covers.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTBundle"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTBundle']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundle(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBundle":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundle`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTBundle(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, name: str) -> "PJTBundle":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int

        :param name: Name for the project part.
        :type part_id: str

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundle`
        """
        db_id = PJTTableBase.insert(self, part_id=part_id, name=name)

        return PJTBundle(self, db_id, self.project_id)


class PJTBundle(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                Visible3DMixin, NameMixin, NotesMixin, SmoothMixin):
    """Represent a PJT bundle in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTBundlesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'pjt_bundles': [self.db_id],
            'bundle_covers': [self.part_id],
            'pjt_points3d': [self.start_position3d_id, self.stop_position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet
    
    _stored_diameter: float | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def diameter(self) -> float:
        if self._stored_diameter is DefaultStoredValue:
            self._stored_diameter = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]
            
        return self._stored_diameter

    @diameter.setter
    def diameter(self, value: float):
        # TODO: figure out the code that is needed here.
        concentric_id = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]

    def get_object(self) -> "_bundle_obj.Bundle":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_bundle_obj.Bundle`
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

    def set_object(self, obj: "_bundle_obj.Bundle"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle_obj.Bundle`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTBundlesTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundlesTable`
        """
        return self._table

    @property
    def length_mm(self) -> float:
        """Straight-line length between this segment's start and stop points, in mm."""
        return _line.Line(self.start_position3d, self.stop_position3d).length()

    @property
    def length_m(self) -> float:
        """Straight-line length between this segment's start and stop points, in meters."""
        return self.length_mm / 1000.0

    @property
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_wire.PJTWire']
        """
        res = []
        for layer in self.concentric.layers:
            res.extend(layer.wires)

        return res
    
    _stored_concentric: "_pjt_concentric.PJTConcentric | None | DefaultStoredValueType" = DefaultStoredValue
    
    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        """Return the concentric.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_concentric.PJTConcentric`
        """
        if self._stored_concentric is DefaultStoredValue:
            concentric_id = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]
            if concentric_id is None:
                self._stored_concentric = None
            else:
                self._stored_concentric = self.table.db.pjt_concentrics_table[concentric_id]
        return self._stored_concentric
        
    @property
    def start_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        """Return the start layout.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: Union['_pjt_bundle_layout.PJTBundleLayout', None]
        """
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.start_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    @property
    def stop_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        """Return the stop layout.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: Union['_pjt_bundle_layout.PJTBundleLayout', None]
        """
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.stop_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    _stored_part: "_bundle_cover.BundleCover | DefaultStoredValueType | None" = DefaultStoredValue
    
    @property
    def part(self) -> "_bundle_cover.BundleCover":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_bundle_cover.BundleCover`
        """
        if self._stored_part is DefaultStoredValue:        
            part_id = self.part_id
            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.bundle_covers_table[part_id]
            
        return self._stored_part


class PJTBundleControl(QTabWidget, LazyTabMixin):
    """Represent a PJT bundle control in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTBundle):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTBundle`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.notes_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.start_stop_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.part_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTBundleControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTBundle = None
        super().__init__(parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.name_ctrl = NameControl(general_page)
        self.notes_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.notes_ctrl)
        general_page.addWidget(self.smooth_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.start_stop_ctrl = StartStopPosition3DControl(position_page)

        position_page.addWidget(self.start_stop_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.part_ctrl = _bundle_cover.BundleCoverControl(part_page)

        part_page.addWidget(self.part_ctrl)

        for page in (
            general_page,
            visible_page,
            position_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
