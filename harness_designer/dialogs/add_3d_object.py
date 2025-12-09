import wx


from .. import image as _image


class AddNewObject(wx.Dialog):

    def __init__(self, parent, image: _image.Image):

        image.bitmap

        button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
