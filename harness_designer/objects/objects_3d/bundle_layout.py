# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ... import config as _config
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout
    from .. import bundle as _bundle_facade
    from ... import ui as _ui


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

    @_check_types.do
    def can_rotate(self) -> bool:
        """A layout waypoint has no independent orientation of its own
        (its ``_angle`` above is a fresh, never-synced dummy purely to
        satisfy ``BaseVar``'s constructor) -- reject the rotation gizmo
        outright rather than relying on the base class's default
        ``self._angle is not None`` check, which would otherwise arm it.
        """
        return False

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

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", bundle: "_bundle_facade.Bundle",
        initial_pos: _point.Point | None = None
    ) -> "_bundle_layout.BundleLayout":
        """Interactive placement of a new waypoint on *bundle*, pinned to
        it for the whole session -- see
        add_handlers.editor_3d.bundle_layout's own module docstring.
        *initial_pos* seeds the live preview's starting position (the
        exact point that was right-clicked to open the "Add Handle" menu
        item, when available) so the preview appears right where the
        user clicked rather than snapping elsewhere first.
        """
        canvas = mainframe.editor3d.editor
        ptables = mainframe.project.ptables

        if initial_pos is None:
            initial_pos = _point.Point(0.0, 0.0, 0.0)

        pos_db = ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        diameter = bundle.obj3d.diameter
        layout_db = ptables.pjt_bundle_layouts_table.insert(pos_db.db_id, diameter)

        from .. import bundle_layout as _bundle_layout_facade

        facade = _bundle_layout_facade.BundleLayout(mainframe, layout_db)
        facade.obj3d.is_visible = False

        from ...add_handlers.editor_3d import bundle_layout as _add_bundle_layout

        handler = _add_bundle_layout.BundleLayout(canvas, facade, bundle)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import bundle_layout as _add_bundle_layout  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_bundle_layout.BundleLayout):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

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
        from PySide6.QtCore import QTimer
        from . import transition as _transition_3d

        mainframe = self.selected.mainframe

        @_check_types.do
        def _do():
            part_id = _menu_ops.get_part_id(
                mainframe, 'transitions',
                mainframe.global_db.transitions_table, 'Add Transition')

            if part_id is None:
                return

            _transition_3d.Transition.start_add(mainframe, part_id)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_delete(self):
        """Delete this bundle layout from the project."""
        _menu_ops.delete_object(self.selected)
