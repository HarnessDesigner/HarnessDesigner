from typing import TYPE_CHECKING

import wx

from .... import utils as _utils

if TYPE_CHECKING:
    from .... import objects as _objects

#
# class AnglePanel(wx.Panel):
#
#     def __init__(self, parent, obj: "_objects.ObjectBase"):
#         wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
#
#         self.obj = obj
#         self.angle3d = obj.db_obj
#
#
#         self.angle2d = obj.obj2d.angle
#
#         wx.StaticBox
#
#         box3d = wx.StaticBox(self, wx.ID_ANY, "3D View")
#
#
#         box2d = wx.StaticBox(self, wx.ID_ANY, "Schematic View")
#
#         text = wx.StaticText(
#             box,
#             wx.ID_ANY,
#             "This window is a child of the staticbox"
#             )
#
#         self.x_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str())
#
#         _utils.HSizer(self, 'X axis:', self.x_ctrl)
#         _utils.HSizer(self, 'Y axis:', self.y_ctrl)
#         _utils.HSizer(self, 'Z axis:', self.z_ctrl)
#
#
#
#
#
#
