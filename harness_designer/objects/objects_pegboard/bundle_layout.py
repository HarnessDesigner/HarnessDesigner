# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from . import chain_edges as _chain_edges
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl.canvas_base import interaction as _interaction
from ... import check_types as _check_types
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout
    from .. import bundle as _bundle_facade
    from ... import ui as _ui


Config = _config.Config.editor_pegboard


class BundleLayout(_base_pegboard.BasePegboard):
    """Represent a bundle layout in :mod:`harness_designer.objects.objects_pegboard.bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_bundle_layout.BundleLayout" = None
    db_obj: "_pjt_bundle_layout.PJTBundleLayout"

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

        # No vbo/angle -- a layout point is a bare position along its
        # bundle's path, no independent rendering presence or rotation of
        # its own (see base_pegboard.BasePegboard.__init__'s vbo-is-None
        # branch). position=None whenever position_pegboard_id is NULL
        # (this layout isn't placed on the peg-board view yet) -- handled
        # gracefully by BaseVar (can_drag()/drag() both no-op on a None
        # position).

        position = db_obj.position_pegboard
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        # Mirrors objects_3d.bundle_layout.BundleLayout.__init__'s own
        # construction exactly: diameter/color come from whatever real
        # bundle this waypoint sits on (its outermost concentric layer's
        # diameter, its part's own color) when it's attached to one,
        # falling back to the row's own bare diameter + a neutral gray
        # when it isn't (unattached waypoint).
        bundles = db_obj.attached_bundles

        if bundles:
            bundle = bundles[-1]
            layers = bundle.concentric.layers
            diameter = layers[-1].diameter
            color = bundle.part.color.ui
        else:
            diameter = db_obj.diameter
            color = _color.Color(0.5, 0.5, 0.5, 1.0)

        scale = _point.Point(diameter, diameter, diameter)
        material = _materials.Rubber(color)

        with parent.mainframe.editor_pegboard.context:
            vbo = _sphere.create_vbo()

            super().__init__(parent, db_obj, vbo, angle,
                             position, scale, material)

        self.point3d_id = db_obj.position_pegboard_id

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
    def touching_budgets(self) -> list:
        """Return the length budget(s) for the bundle segment(s) touching
        this waypoint -- always two (previous/next), since a
        bundle-layout point is always strictly interior to its bundle's
        chain.

        Resolves this waypoint's own row (``pjt_points_pegboard``) to
        find which bundle it belongs to, then delegates the actual chain
        walk to that bundle's own
        ``objects.objects_pegboard.bundle.Bundle.touching_edges``.
        """
        if self.point3d_id is None:
            return []

        project = self.parent.mainframe.project
        waypoint_row = project.ptables.pjt_points_pegboard_table[self.point3d_id]

        if waypoint_row.bundle_id is None:
            return []

        bundle_db_obj = project.ptables.pjt_bundles_table[waypoint_row.bundle_id]
        return _chain_edges.touching_edges(bundle_db_obj, self.point3d_id)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", bundle: "_bundle_facade.Bundle",
        initial_pos: _point.Point | None = None
    ) -> "_bundle_layout.BundleLayout":
        """Interactive placement of a new waypoint on *bundle*'s own
        pegboard chain, pinned to it for the whole session -- see
        add_handlers.editor_pegboard.bundle_layout's own module
        docstring. *initial_pos* seeds the live preview's starting
        pegboard position (the point that was right-clicked to open the
        "Add Waypoint" menu item, when available).
        """
        canvas = mainframe.editor_pegboard.editor
        ptables = mainframe.project.ptables

        if initial_pos is None:
            initial_pos = _point.Point(0.0, 0.0, 0.0)

        pos_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        layout_db = ptables.pjt_bundle_layouts_table.insert(pos_db.db_id, bundle.obj3d.diameter)

        from .. import bundle_layout as _bundle_layout_facade

        facade = _bundle_layout_facade.BundleLayout(mainframe, layout_db)
        facade.objpegboard.is_visible = False

        pos = facade.objpegboard.position
        pos += initial_pos - pos

        from ...add_handlers.editor_pegboard import bundle_layout as _add_bundle_layout

        handler = _add_bundle_layout.BundleLayout(canvas, facade, bundle)
        facade.objpegboard._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objpegboard

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to BasePegboard's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_pegboard import bundle_layout as _add_bundle_layout  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_bundle_layout.BundleLayout):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)
