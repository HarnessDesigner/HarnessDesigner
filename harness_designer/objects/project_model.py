# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import project_model as _project_model_2d
from .objects3d import project_model as _project_model_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import project as _project


class ProjectModel(_ObjectBase):
    """Represent a boot in :mod:`harness_designer.objects.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _project_model_2d.ProjectModel = None
    obj3d: _project_model_3d.ProjectModel = None
    db_obj: "_project.Project" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_project.Project", vbo):

        super().__init__(mainframe, db_obj)

        print('constructing  model')

        self.obj2d = _project_model_2d.ProjectModel(self, db_obj)
        self.obj3d = _project_model_3d.ProjectModel(self, db_obj, vbo)
        self.mainframe.add_object(self)

    def set_selected(self, flag):
        pass

    def is_selected(self) -> bool:
        return False
