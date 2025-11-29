
from typing import TYPE_CHECKING, Iterator as _Iterator
import wx

from ..config import Config as _Config

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db import pjt_bundle as _pjt_bundle
    from ..database.project_db import pjt_point_2d as _pjt_point_2d
    from ..database.project_db import pjt_point_3d as _pjt_point_3d
    from ..database.project_db import pjt_transition as _pjt_transition
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from ..database.project_db import pjt_housing as _pjt_housing
    from ..database.project_db import pjt_wire2d_layout as _pjt_wire2d_layout
    from ..database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout
    from ..database.project_db import pjt_splice as _pjt_splice


class Config(metaclass=_Config):
    recent_projects = []


class Project:

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        self.gtables = mainframe.global_db
        self.connector = mainframe.db_connector
        self.project_id = None
        self.project_name = ''

        from ..database import project_db

        self.ptables = project_db.PJTTables(self.mainframe)

    def select_project(self):
        from ..dialogs.project_dialog import OpenProjectDialog

        project_names = []

        self.connector.execute(f'SELECT name FROM projects;')
        for name in self.connector.fetchall():
            project_names.append(name[0])

        dlg = OpenProjectDialog(self.mainframe, Config.recent_projects, project_names)

        try:
            if dlg.ShowModal() != wx.ID_CANCEL:
                project_name = dlg.GetValue()
            else:
                self.project_name = None
                return False
        finally:
            dlg.Destroy()

        self.connector.execute(f'SELECT id FROM projects WHERE name = "{project_name}";')
        res = self.connector.fetchall()

        if res:
            self.project_id = res[0][0]
        else:
            self.connector.execute(f'INSERT INTO projects (name) VALUES (?);', (project_name,))
            self.connector.commit()
            self.project_id = self.connector.lastrowid

        self.mainframe.obj_count = self.ptables.projects_table.get_object_count(self.project_id)
        self.ptables.load(self.project_id)

        return True

    @property
    def transitions(self) -> _Iterator["_pjt_transition.PJTTransition"]:
        for transition in self.ptables.pjt_transitions_table:
            yield transition

    @property
    def housings(self) -> _Iterator["_pjt_housing.PJTHousing"]:
        for housing in self.ptables.pjt_housings_table:
            yield housing

    @property
    def splices(self) -> _Iterator["_pjt_splice.PJTSplice"]:
        for splice in self.ptables.pjt_splices_table:
            yield splice

    @property
    def wires(self) -> _Iterator["_pjt_wire.PJTWire"]:
        for wire in self.ptables.pjt_wires_table:
            yield wire

    @property
    def wire_2d_layouts(self) -> _Iterator["_pjt_wire2d_layout.PJTWire2DLayout"]:
        for layout in self.ptables.pjt_wire_2d_layouts_table:
            yield layout

    @property
    def wire_3d_layouts(self) -> _Iterator["_pjt_wire3d_layout.PJTWire3DLayout"]:
        for layout in self.ptables.pjt_wire_3d_layouts_table:
            yield layout

    @property
    def bundles(self) -> _Iterator["_pjt_bundle.PJTBundle"]:
        for bundle in self.ptables.pjt_bundles_table:
            yield bundle

    @property
    def bundle_layouts(self) -> _Iterator["_pjt_bundle_layout.PJTBundleLayout"]:
        for layout in self.ptables.pjt_bundle_layouts_table:
            yield layout

    @property
    def points2d(self) -> _Iterator["_pjt_point_2d.PJTPoint2D"]:
        for point in self.ptables.pjt_points_2d_table:
            yield point

    @property
    def points3d(self) -> _Iterator["_pjt_point_3d.PJTPoint3D"]:
        for point in self.ptables.pjt_points_3d_table:
            yield point

    @property
    def recent_projects(self) -> _Iterator:
        return Config.recent_projects[:]
