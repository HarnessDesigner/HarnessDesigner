


x_offset = -26.2
y_offset = 0.0
z_offset = 0.0


x_offset = 26.2
y_offset = 0.0
z_offset = 0.0


x_offset = 0.0
y_offset = 19.3
z_offset = 0.0


x_rotate

y_rotate

z_rotate


class Branch:

    def __init__(self, transition, schematic_pos, editor_pos, offset_x, offset_y, offset_z):
        self._transition = transition
        self._plot_obj = None
        self._schematic_pos = schematic_pos
        self._editor_pos = editor_pos
        self._bundle = None
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._offset_z = offset_z


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


class BranchData:

    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0
        self.color = 0

class Transition:

    def __init__(self, schematic_pos, editor_pos, branches):
        self._schematic_pos = schematic_pos
        self._editor_pos = editor_pos
        self._plot_obj = None

        self._branches = branches

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