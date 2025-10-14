

class Layout:

    def __init__(self, wire_or_bundle1, schematic_pos, editor_pos):
        self._schematic_pos = schematic_pos
        self._editor_pos = editor_pos

        wire_or_bundle2 = wire_or_bundle1.AddLayout(self)
        self._wires_or_bundles = [wire_or_bundle1, wire_or_bundle2]
        self._obj = None

    def SetPlotObject(self, obj):
        self._obj = obj

    def SetSchematicPosition(self, pos):
        self._schematic_pos = pos

    def GetSchematicPosition(self):
        return self._schematic_pos

    def SetEditorPosition(self, pos):
        for obj in self._wires_or_bundles:
            obj.SetEditorPosition(pos)

        self._editor_pos = pos

        x, y, z = pos
        self._obj._offsets3d[0][0] = x  # NOQA
        self._obj._offsets3d[1][0] = y  # NOQA
        self._obj._offsets3d[2][0] = z  # NOQA

    def GetEditorPosition(self):
        return self._editor_pos
