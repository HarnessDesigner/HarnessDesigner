# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ..gl import materials as _materials
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from .objects_3d import base_3d as _base_3d
    from .objects_schematic import base_schematic as _base_schematic
    from .objects_pegboard import base_pegboard as _base_pegboard
    from ..database import project_db as _project_db


class ObjectBase:
    """Represent an object base in :mod:`harness_designer.objects.object_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: "_base_schematic.BaseSchematic" = None
    obj3d: "_base_3d.Base3D" = None
    objpegboard: "_base_pegboard.BasePegboard" = None
    db_obj: "_project_db.PJTEntryBase" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_project_db.PJTEntryBase"):
        """Initialise the :class:`ObjectBase` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project_db.PJTEntryBase`
        """
        self.mainframe: "_ui.MainFrame" = mainframe

        self._deleted = False
        self._is_selected = False
        self._treeitem = None
        self.db_obj = db_obj

    @_check_types.do
    def identify(self, material: _materials.GLMaterial | None) -> None:
        """Execute the identify operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param material: Value for ``color``.
        :type material: list[float] | None
        """
        if self.objschematic is not None:
            self.objschematic.identify(material)

        if self.obj3d is not None:
            self.obj3d.identify(material)

        if self.objpegboard is not None:
            self.objpegboard.identify(material)

    @_check_types.do
    def set_treeitem(self, treeitem) -> None:
        """Set the treeitem.

        UNKNOWN details are inferred from the callable name and signature.

        :param treeitem: Value for ``treeitem``.
        :type treeitem: UNKNOWN
        """
        self._treeitem = treeitem

    @_check_types.do
    def get_treeitem(self):
        """Return the treeitem.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._treeitem

    @_check_types.do
    def delete(self) -> None:
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self._deleted:
            return

        self._deleted = True

        if self.objschematic is not None:
            self.objschematic._delete()  # NOQA

        if self.obj3d is not None:
            self.obj3d._delete()  # NOQA

        if self.objpegboard is not None:
            self.objpegboard._delete()  # NOQA

        self.mainframe.remove_object(self)

    @_check_types.do
    def close(self) -> None:
        """Execute the close operation.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        # TODO: This function will be used to remove the object from editors
        #       but it will not delete itself from the database. I need to do
        #       some more work on an object type basis to make sure I am not
        #       accidentally deleting something I shuldn't be.
        raise NotImplementedError

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self._is_selected = flag

        if self.objschematic is not None:
            self.objschematic.set_selected(flag)

        if self.obj3d is not None:
            self.obj3d.set_selected(flag)

        if self.objpegboard is not None:
            self.objpegboard.set_selected(flag)

        if flag:
            self.mainframe._set_selected(self)  # NOQA
        else:
            self.mainframe._set_selected(None)  # NOQA

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        """Return the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_selected

    @is_selected.setter
    @_check_types.do
    def is_selected(self, value: bool):
        """Set the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_selected = value

        if self.objschematic is not None and self.objschematic.is_selected != value:
            self.objschematic.set_selected(value)

        if self.obj3d is not None and self.obj3d.is_selected != value:
            self.obj3d.set_selected(value)

        if self.objpegboard is not None and self.objpegboard.is_selected != value:
            self.objpegboard.set_selected(value)

    @property
    @_check_types.do
    def is_in_3dview(self) -> bool:
        return self in self.mainframe.editor3d.camera.objects_in_view

    @property
    @_check_types.do
    def is_in_2dview(self) -> bool:
        return self in self.mainframe.editor2d.editor.camera.objects_in_view

    @property
    @_check_types.do
    def is_in_pegboardview(self) -> bool:
        return self in self.mainframe.editor_pegboard.editor.camera.objects_in_view

    @property
    @_check_types.do
    def is_boot(self) -> bool:
        from . import boot as _boot

        return isinstance(self, _boot.Boot)

    @property
    @_check_types.do
    def is_bundle(self) -> bool:
        from . import bundle as _bundle

        return isinstance(self, _bundle.Bundle)

    @property
    @_check_types.do
    def is_bundle_layout(self) -> bool:
        from . import bundle_layout as _bundle_layout

        return isinstance(self, _bundle_layout.BundleLayout)

    @property
    @_check_types.do
    def is_cavity(self) -> bool:
        from . import cavity as _cavity

        return isinstance(self, _cavity.Cavity)

    @property
    @_check_types.do
    def is_circuit(self) -> bool:
        from . import circuit as _circuit

        return isinstance(self, _circuit.Circuit)

    @property
    @_check_types.do
    def is_cover(self) -> bool:
        from . import cover as _cover

        return isinstance(self, _cover.Cover)

    @property
    @_check_types.do
    def is_cpa_lock(self) -> bool:
        from . import cpa_lock as _cpa_lock

        return isinstance(self, _cpa_lock.CPALock)

    @property
    @_check_types.do
    def is_housing(self) -> bool:
        from . import housing as _housing

        return isinstance(self, _housing.Housing)

    @property
    @_check_types.do
    def is_note(self) -> bool:
        from . import note as _note

        return isinstance(self, _note.Note)

    @property
    @_check_types.do
    def is_project(self) -> bool:
        from . import project as _project

        return isinstance(self, _project.Project)

    @property
    @_check_types.do
    def is_seal(self) -> bool:
        from . import seal as _seal

        return isinstance(self, _seal.Seal)

    @property
    @_check_types.do
    def is_splice(self) -> bool:
        from . import splice as _splice

        return isinstance(self, _splice.Splice)

    @property
    @_check_types.do
    def is_terminal(self) -> bool:
        from . import terminal as _terminal

        return isinstance(self, _terminal.Terminal)

    @property
    @_check_types.do
    def is_tpa_lock(self) -> bool:
        from . import tpa_lock as _tpa_lock

        return isinstance(self, _tpa_lock.TPALock)

    @property
    @_check_types.do
    def is_transition(self) -> bool:
        from . import transition as _transition

        return isinstance(self, _transition.Transition)

    @property
    @_check_types.do
    def is_wire(self) -> bool:
        from . import wire as _wire

        return isinstance(self, _wire.Wire)

    @property
    @_check_types.do
    def is_wire_layout(self) -> bool:
        from . import wire_layout as _wire_layout

        return isinstance(self, _wire_layout.WireLayout)

    @property
    @_check_types.do
    def is_wire_marker(self) -> bool:
        from . import wire_marker as _wire_marker

        return isinstance(self, _wire_marker.WireMarker)

    @property
    @_check_types.do
    def is_wire_service_loop(self) -> bool:
        from . import wire_service_loop as _wire_service_loop

        return isinstance(self, _wire_service_loop.WireServiceLoop)
