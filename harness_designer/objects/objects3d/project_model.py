# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils
from ... import color as _color


if TYPE_CHECKING:
    from ...database.project_db import project as _project
    from .. import project_model as _project_model


Config = _config.Config.editor3d


class ProjectModel(_base3d.Base3D):
    parent: "_project_model.ProjectModel" = None
    db_obj: "_project.Project" = None

    def __init__(self, parent: "_project_model.ProjectModel", db_obj: "_project.Project", vbo):
        parent.mainframe.editor3d.context.acquire()

        color = db_obj.color.ui
        scale = _point.Point(10.0, 10.0, 10.0)
        position = _point.Point(0.0, 0.0, 0.0)
        material = _materials.Plastic(color)
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, position, scale, material)

        parent.mainframe.editor3d.context.release()
        self._is_visible = True
        self.mainframe.editor3d.Refresh()

    @property
    def smooth(self):
        return True

    def get_context_menu(self):
        pass

    def render(self, faces_program, edges_program, vertices_program):
        super().render(faces_program, edges_program, vertices_program)
