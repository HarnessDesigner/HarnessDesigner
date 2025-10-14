

class Terminal:

    def __init__(self, index, offset_x, offset_y, schematic_position, _=None):
        self.index = index
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._housing = None
        self._schematic_pos = (0, 0)
        self._schematic_position = schematic_position
        self._wires = []

    def SetPlotObject(self, _):
        pass

    def SetHousing(self, housing):
        self._housing = housing

    def GetHousing(self):
        return self._housing

    def SetSchematicPosition(self, pos):
        x, y = pos
        x += self._offset_x
        y += self._offset_y
        self._schematic_pos = (x, y)

    def GetSchematicPosition(self):
        return self._schematic_pos

    def SetEditorPosition(self, pos):
        for wire in self._wires:
            wire.SetEditorPosition(pos)

    def GetEditorPosition(self):
        return self._housing.GetEditorPosition()

    def AddWire(self, wire):
        wire.AddEndpoint(self)

    def RemoveWire(self, wire):
        wire.RemoveEndpoint(self)
