# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ... import config as _config
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


Config = _config.Config.editor_3d


class BundleLayout(_base_3d.Base3D):
    """Represent a bundle layout in :mod:`harness_designer.objects.objects_3d.bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_bundle_layout.BundleLayout" = None
    db_obj: "_pjt_bundle_layout.PJTBundleLayout" = None

    # Sits on the bundle's centerline, inside its OBB by design -- see
    # Base3D._pick_priority.
    _pick_priority = 1

    @_check_types.do
    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):
        """Initialise the :class:`BundleLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle_layout.BundleLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle_layout.PJTBundleLayout`
        """

        with parent.mainframe.editor3d.context:
            bundles = db_obj.attached_bundles

            if bundles:
                bundle = bundles[-1]
                layers = bundle.concentric.layers
                self._diameter = layers[-1].diameter
                color = bundle.part.color.ui
            else:
                self._diameter = db_obj.diameter
                color = _color.Color(0.5, 0.5, 0.5, 1.0)

            material = _materials.Rubber(color)

            scale = _point.Point(self._diameter, self._diameter, self._diameter)
            vbo = _sphere.create_vbo()
            angle = _angle.Angle()
            position = db_obj.position3d

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_bundles

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def set_diameter(self, value: float):
        """Set this layout's own displayed diameter to match whatever
        bundle it sits on.

        A BundleLayout is always an ordinary interior waypoint of exactly
        one bundle now (or none, if unattached) -- it never marks a
        boundary between two separate bundle rows any more (see
        objects.objects_3d.bundle.Bundle.set_diameter), so there is no
        sibling bundle at this same position left to cascade into.
        """
        self._diameter = value
        scale = _point.Point(value, value, value)
        diff = self._scale - scale
        self._scale += diff

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return BundleLayoutMenu(self.mainframe.editor3d.editor, self)


class BundleLayoutMenu(QMenu):
    """Represent a bundle layout menu in :mod:`harness_designer.objects.objects_3d.bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`BundleLayoutMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Transition')
        action.triggered.connect(self.on_add_transition)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

    @_check_types.do
    def on_add_transition(self):
        """Start the interactive transition placement flow."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        @_check_types.do
        def _factory():
            part_id = _menu_ops.get_part_id(
                mainframe, 'transitions',
                mainframe.global_db.transitions_table, 'Add Transition')

            if part_id is None:
                return None

            return _handlers.AddTransitionHandler(mainframe, part_id)

        _menu_ops.start_handler(mainframe, _factory)

    @_check_types.do
    def on_delete(self):
        """Delete this bundle layout from the project."""
        _menu_ops.delete_object(self.selected)
