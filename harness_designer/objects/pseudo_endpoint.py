
class PseudoEndpoint:

    def __init__(self, schematic_pos, editor_pos):
        self._housing = None
        self._schematic_pos = schematic_pos
        self._editor_pos = editor_pos
        self._obj = None

    def SetPlotObject(self, obj):
        self._obj = obj

    def SetSchematicPosition(self, pos):
        self._schematic_pos = pos

    def GetSchematicPosition(self):
        return self._schematic_pos

    def SetEditorPosition(self, pos):
        self._editor_pos = pos

    def GetEditorPosition(self):
        return self._editor_pos

    def AddWire(self, wire):
        wire.AddEndpoint(self)

    def RemoveWire(self, wire):
        wire.RemoveEndpoint(self)

