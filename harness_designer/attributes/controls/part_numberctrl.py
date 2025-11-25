from . import generic_textctrl as _generic_textctrl


class PartNumberCtrl(_generic_textctrl.GenericTextCtrl):

    def __init__(self, parent):
        _generic_textctrl.GenericTextCtrl.__init__(self, parent, 'Part Number:')
