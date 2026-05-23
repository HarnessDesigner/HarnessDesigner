# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu, QDialog
from PySide6.QtCore import QTimer, Qt

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry.decimal import Decimal as _d
from ...ui.dialogs import housing_editor as _housing_editor
from . import base3d as _base3d
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor3d


class Housing(_base3d.Base3D):
    """Represent a housing in :mod:`harness_designer.objects.objects3d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part

        angle = db_obj.angle3d
        color = self._part.color.ui
        material = _materials.Plastic(color)

        model = self._part.model3d

        if model is not None:
            uuid = model.uuid
            scale = _point.Point(1.0, 1.0, 1.0)

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_housings:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)

        else:
            vbo = _box.create_vbo()
            scale = self._part.scale

        vbo.acquire()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)
        parent.mainframe.editor3d.context.release()

    @property
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.seal_position3d

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return HousingMenu(self.mainframe, self)


class HousingMenu(QMenu):
    """Represent a housing menu in :mod:`harness_designer.objects.objects3d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_ui.MainFrame", obj: Housing):
        """Initialise the :class:`HousingMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param obj: Object instance to operate on.
        :type obj: :class:`Housing`
        """
        QMenu.__init__(self)
        self.mainframe = mainframe
        self.canvas = mainframe.editor3d.editor
        self.obj = obj

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add CPA Lock')
        action.triggered.connect(self.on_add_cpa_lock)

        action = self.addAction('Add TPA Lock')
        action.triggered.connect(self.on_add_tpa_lock)

        action = self.addAction('Add Cover')
        action.triggered.connect(self.on_add_cover)

        action = self.addAction('Add Boot')
        action.triggered.connect(self.on_add_boot)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(self.canvas, obj)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(self.canvas, obj)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

        action = self.addAction('Housing Editor')
        action.triggered.connect(self.on_housing_editor)

    def on_housing_editor(self):
        """Handle the housing editor event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: UNKNOWN
            """
            dlg = _housing_editor.HousingEditorDialog(self.mainframe, housing)
            dlg.exec()

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj.part))

    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.

        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        def _do(housing: "_pjt_housing.PJTHousing"):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: :class:`_pjt_housing.PJTHousing`
            :raises RuntimeError: Raised when the operation cannot be completed.
            """
            dlg = _pjt_add_seal.AddSealDialog(self.mainframe, housing)
            if dlg.exec() == QDialog.Accepted:
                part_id, db_id = dlg.GetValue()
                obj_type = dlg.GetObjectType()

                if obj_type == _pjt_add_seal.CAVITY:
                    self.mainframe.project.add_seal(part_id, cavity_id=db_id)
                elif obj_type == _pjt_add_seal.TERMINAL:
                    self.mainframe.project.add_seal(part_id, terminal_id=db_id)
                elif obj_type == _pjt_add_seal.HOUSING:
                    self.mainframe.project.add_seal(part_id, housing_id=db_id)
                else:
                    raise RuntimeError('sanity check')

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj))

    def on_add_terminal(self):
        """Handle the add terminal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing: "_pjt_housing.PJTHousing"):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: :class:`_pjt_housing.PJTHousing`
            """
            dlg = _pjt_add_terminal.AddTerminalDialog(self.mainframe, housing)

            if dlg.exec() == QDialog.Accepted:
                part_id, db_id = dlg.GetValue()
                self.mainframe.project.add_terminal(part_id, cavity_id=db_id)

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj))

    def on_add_cpa_lock(self):
        """Handle the add CPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing: "_pjt_housing.PJTHousing"):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: :class:`_pjt_housing.PJTHousing`
            """
            dlg = _pjt_add_cpa_lock.AddCPALockDialog(self.mainframe, housing)

            if dlg.exec() == QDialog.Accepted:
                part_id = dlg.GetValue()
                self.mainframe.project.add_cpa_lock(part_id, housing_id=housing.db_id)

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj))

    def on_add_tpa_lock(self):
        """Handle the add TPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing: "_pjt_housing.PJTHousing"):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: :class:`_pjt_housing.PJTHousing`
            """
            dlg = _pjt_add_tpa_lock.AddTPALockDialog(self.mainframe, housing)

            if dlg.exec() == QDialog.Accepted:
                part_id, idx = dlg.GetValue()
                self.mainframe.project.add_tpa_lock(part_id, idx=idx, housing_id=housing.db_id)

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj))

    def on_add_cover(self):
        """Handle the add cover event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing: "_pjt_housing.PJTHousing"):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: :class:`_pjt_housing.PJTHousing`
            """
            dlg = _pjt_add_cover.AddCoverDialog(self.mainframe, housing)

            if dlg.exec() == QDialog.Accepted:
                part_id = dlg.GetValue()
                self.mainframe.project.add_cover(part_id, housing_id=housing.db_id)

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj))

    def on_add_boot(self):
        """Handle the add boot event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        def _do(housing: "_pjt_housing.PJTHousing"):
            """Execute the do operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param housing: Value for ``housing``.
            :type housing: :class:`_pjt_housing.PJTHousing`
            """
            dlg = _pjt_add_boot.AddBootDialog(self.mainframe, housing)

            if dlg.exec() == QDialog.Accepted:
                part_id = dlg.GetValue()
                self.mainframe.project.add_boot(part_id, housing_id=housing.db_id)

        QTimer.singleShot(0, lambda: _do(self.obj.db_obj))

    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        selected = self.mainframe.get_selected()

        if selected is not None:
            selected.set_selected(False)

        self.obj.set_selected(True)

    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.mainframe.editor3d.setCursor(Qt.CursorShape.CrossCursor)
        self.mainframe.set_clone_obj(self.obj.parent)

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.obj.delete()

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
