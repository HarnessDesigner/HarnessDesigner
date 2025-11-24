# TODO: Boot attributes panel
import wx

'''
part_number str
manufacturer Manufacturer gloabl_db.manufacturer_table.choices
description str
family str gloabl_db.families_table.choices
series str gloabl_db.series_table.choices
min_temp str gloabl_db.temperatures_table.choices
max_temp str gloabl_db.temperatures_table.choices
color Color
weight _decimal

cad
image
datasheet
model3d
'''

class BootAttribPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

