# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import project as _project
    from .. import project_model as _project_model


class ProjectModel(_base2d.Base2D):
    _parent: "_project_model.ProjectModel" = None
    db_obj: "_project.Project" = None

    def __init__(self, parent: "_project_model.ProjectModel", db_obj: "_project.Project"):
        _base2d.Base2D.__init__(self, parent, db_obj, None, None)
