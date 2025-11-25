from . import generic_floatctrl as _generic_floatctrl


class WeightCtrl(_generic_floatctrl.GenericFloatCtrl):

    def __init__(self, parent):
        _generic_floatctrl.GenericFloatCtrl.__init__(self, parent, 'Weight:', 'g')
