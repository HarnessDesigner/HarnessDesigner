from wx import propgrid as wxpg


class LongStringProperty(wxpg.LongStringProperty):

    def __init__(self, label, name, value, dialog_label=''):
        wxpg.LongStringProperty.__init__(label, name, value)

        if dialog_label:
            self.SetAttribute(wxpg.PG_DIALOG_TITLE, dialog_label)