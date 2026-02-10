import wx


class RemoveDBRecordDialog(wx.MessageDialog):

    def __init__(self, parent, record_type, record_name):

        caption = 'Remove Database Record'

        message = (
            f'Are you sure you want to remove "{record_name}" from the "{record_type}" Database?\n\n'
            'WARNING: This action cannot be undone!\n'
            'NOTE: This action might effect other records in the database.'
        )
        wx.MessageDialog.__init__(self, parent, caption=caption, message=message,
                                  style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_HAND | wx.STAY_ON_TOP | wx.CENTRE)
