
from typing import TYPE_CHECKING


from ..shapes import cylinder as _cylinder
from ..shapes import sphere as _sphere
from ..shapes import hemisphere as _hemisphere
from ..geometry import point as _point
from ..geometry import line as _line
from ..wrappers.decimal import Decimal as _decimal


if TYPE_CHECKING:
    from ..ui import mainframe as _mainframe
    from .. import editor_2d as _editor2d
    from .. import editor_3d as _editor3d
    from ..database.project_db import pjt_transition as _pjt_transition
    from ..database.global_db import transition_branch as _transition_branch


class Branch:

    def __init__(self, transition: "Transition", origin: _point.Point, branch: "_transition_branch.TransitionBranch"):
        self._transition = transition
        self._origin = origin
        self._origin.Bind(self.on_move)
        self._branch = branch

        self.length = branch.length
        self.index = branch.idx

        self._angle = branch.angle
        self._offset = branch.offset
        self._bulb_len = branch.bulb_length
        self._bulb_offset = branch.bulb_offset
        self._flange_height = branch.flange_height
        self._flang_width = branch.flange_width
        self._max_dia = branch.max_dia
        self._min_dia = branch.min_dia
        self._dia = self._min_dia
        self._objs = []

        center = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))

        if self._bulb_len not in (None, 0.0):
            if self._bulb_offset is not None:
                offset_x, offset_y = self._bulb_offset
                p1 = center.copy()
                p1.x += _decimal(offset_x)
                p1.y += _decimal(offset_y)
                _hemisphere.Hemisphere()

                self._dia

                self._bulb_offset

    @property
    def name(self):
        return self._branch.name

    def remove(self):
        pass

    def on_move(self, point):
        pass

    def set_diameter(self, dia):
        if self._max_dia < dia:
            return False
        elif self._min_dia > dia:
            return False
        self._dia = dia

    def SetSchematicPosition(self, pos):
        self._schematic_pos = pos

    def GetSchematicPosition(self):
        return self._schematic_pos

    def SetEditorPosition(self, pos):
        self._bundle.SetEditorPosition()

        x, y, z = pos

        self._plot_obj._offsets3d[0][0] = x  # NOQA
        self._plot_obj._offsets3d[1][0] = y  # NOQA
        self._plot_obj._offsets3d[2][0] = z  # NOQA

        self._editor_pos = pos

    def GetEditorPosition(self):

        return self._editor_pos

    def SetPlotObject(self, obj):
        self._plot_obj = obj

    def SetBundle(self, bundle):
        self._bundle = bundle

    def GetBundle(self):
        return self._bundle


class Transition:

    def __init__(self, transition: "_pjt_transition.PJTTransition", mainframe: "_mainframe.MainFrame", editor_2d: "_editor2d.Editor2D", editor_3d: "_editor3d.Editor3D"):
        self.editor_2d = editor_2d
        self.editor_3d = editor_3d
        self.mainframe = mainframe
        self.global_db = mainframe.global_db
        self.project = mainframe.project
        self._transition = transition

        transition.x_angle
        transition.y_angle
        transition.z_angle

        transition.point

        transition.name

        part = transition.part
        bc = part.branch_count
        branches = part.branches

        transition.branch1_point
        branches[0]

        if bc < 3:
            transition.branch2_point
            branches[1]
        if bc < 4:
            transition.branch3_point
            branches[2]

        if bc < 5:
            transition.branch4_point
            branches[3]
        if bc < 6:
            transition.branch5_point
            branches[4]
        if bc < 7:
            transition.branch6_point
            branch = branches[5]

        # for branch in part.branches:
        #
        # self.editor_3d.
        #
        # self._schematic_pos = schematic_pos
        # self._editor_pos = editor_pos
        # self._plot_obj = None
        #
        # self._branches = branches

    def SetPlotObject(self, obj):
        self._plot_obj = obj

    def SetSchematicPosition(self, pos):
        self._schematic_pos = pos

    def GetSchematicPosition(self):
        return self._schematic_pos

    def SetEditorPosition(self, pos):

        for branch in self._branches:
            branch.SetEditorPosition(pos)

        self._editor_pos = pos

        x, y, z = pos
        self._plot_obj._offsets3d[0][0] = x  # NOQA
        self._plot_obj._offsets3d[1][0] = y  # NOQA
        self._plot_obj._offsets3d[2][0] = z  # NOQA