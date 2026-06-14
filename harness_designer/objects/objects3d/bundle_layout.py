# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


Config = _config.Config.editor3d.renderer


class BundleLayout(_base3d.Base3D):
    """Represent a bundle layout in :mod:`harness_designer.objects.objects3d.bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_bundle_layout.BundleLayout" = None
    db_obj: "_pjt_bundle_layout.PJTBundleLayout" = None

    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):
        """Initialise the :class:`BundleLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle_layout.BundleLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle_layout.PJTBundleLayout`
        """

        parent.mainframe.editor3d.context.acquire()
        bundles = db_obj.attached_bundles

        bundle = bundles[-1]
        layers = bundle.concentric.layers
        self._diameter = layers[-1].diameter

        color = bundle.part.color.ui
        material = _materials.Rubber(color)

        scale = _point.Point(self._diameter, self._diameter, self._diameter)
        vbo = _sphere.create_vbo()
        angle = _angle.Angle()
        position = db_obj.position3d

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        parent.mainframe.editor3d.context.release()

    def set_diameter(self, parent_bundle, value: float):
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent_bundle: Value for ``parent_bundle``.
        :type parent_bundle: UNKNOWN
        :param value: Value to store or process.
        :type value: float
        """
        self._diameter = value
        scale = _point.Point(value, value, value)
        diff = self._scale - scale
        self._scale += diff

        for bundle in self.editor3d.mainframe.project.bundles:
            if (
                bundle.obj3d.position.db_id == self.position.db_id and
                parent_bundle != bundle.obj3d
            ):
                bundle.obj3d.set_diameter(self, value)
                break

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return BundleLayoutMenu(self.mainframe.editor3d.editor, self)


class BundleLayoutMenu(QMenu):
    """Represent a bundle layout menu in :mod:`harness_designer.objects.objects3d.bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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

    def on_add_transition(self):
        """Start the interactive transition placement flow."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        def _factory():
            part_id = _menu_ops.get_part_id(
                mainframe, 'transitions',
                mainframe.global_db.transitions_table, 'Add Transition')

            if part_id is None:
                return None

            return _handlers.AddTransitionHandler(mainframe, part_id)

        _menu_ops.start_handler(mainframe, _factory)

    def on_delete(self):
        """Delete this bundle layout from the project."""
        _menu_ops.delete_object(
            self.selected,
            self.selected.mainframe.project.delete_bundle_layout)
