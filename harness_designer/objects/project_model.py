# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_schematic import project_model as _project_model_schematic
from .objects_3d import project_model as _project_model_3d
from .objects_pegboard import project_model as _project_model_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import project as _project


class ProjectModel(_ObjectBase):
    """Represent a boot in :mod:`harness_designer.objects.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _project_model_schematic.ProjectModel = None
    obj3d: _project_model_3d.ProjectModel = None
    objpegboard: _project_model_pegboard.ProjectModel = None
    db_obj: "_project.Project" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_project.Project", vbo):

        super().__init__(mainframe, db_obj)

        self.objschematic = _project_model_schematic.ProjectModel(self, db_obj)
        self.obj3d = _project_model_3d.ProjectModel(self, db_obj, vbo)
        self.objpegboard = _project_model_pegboard.ProjectModel(self, db_obj)
        self.mainframe.add_object(self)

    @_check_types.do
    def set_selected(self, flag):
        pass

    @_check_types.do
    def is_selected(self) -> bool:
        return False
