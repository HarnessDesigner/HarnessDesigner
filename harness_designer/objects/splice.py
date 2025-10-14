

class Splice:

    def __init__(self, schematic_pos, editor_pos, wire1):
        self._schematic_pos = schematic_pos
        self._editor_pos = editor_pos

        wire2 = wire1.AddSplice(self)
        self._wires = [wire1, wire2]
        self._plot_obj = None

    def SetPlotObject(self, obj):
        self._plot_obj = obj

    def SetSchematicPosition(self, pos):
        self._schematic_pos = pos

    def GetSchematicPosition(self):
        return self._schematic_pos

    def SetEditorPosition(self, pos):
        for wire in self._wires:
            wire.SetEditorPosition(pos)

        self._editor_pos = pos

        x, y, z = pos
        self._plot_obj._offsets3d[0][0] = x  # NOQA
        self._plot_obj._offsets3d[1][0] = y  # NOQA
        self._plot_obj._offsets3d[2][0] = z  # NOQA

    def GetEditorPosition(self):
        return self._editor_pos

    def AddWire(self, wire):
        wire.AddEndpoint(self)
        self._wires.append(self)

    def RemoveWire(self, wire):
        self._wires.remove(wire)
        wire.RemoveEndpoint(self)
