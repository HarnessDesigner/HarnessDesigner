

class Bundle:

    def __init__(self, wires):
        for wire in wires:
            wire.Show(False)

        self._wires = wires
        self._endpoint1 = None
        self._endpoint2 = None
        self._plot_obj = None

    def SetPlotObject(self, obj):
        self._plot_obj = obj

    def AddLayout(self, layout):
        bundle = Bundle(layout)
        bundle.AddEndpoint(self._endpoint2)
        self._endpoint2 = layout
        return bundle

    def AddEndpoint(self, obj):
        if self._endpoint1 is None:
            self._endpoint1 = obj
        elif self._endpoint2 is None:
            self._endpoint2 = obj

    def RemoveEndpoint(self, obj):
        if self._endpoint1 == obj:
            self._endpoint1 = None
        elif self._endpoint2 == obj:
            self._endpoint2 = None

    def Delete(self):
        for wire in self._wires:
            wire.Show(True)
