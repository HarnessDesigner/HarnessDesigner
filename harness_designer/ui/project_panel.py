
import wx

class ProjectPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.tree = wx.TreeCtrl(self, wx.ID_ANY, style=wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_TWIST_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE)
        self.tree.AddRoot('root')

        'Circuits'
        'Transitions'
        'Wires'
        'Connectors'
        'Housings'
        'Terminals'
        'Bundles'
        'Splices'



AppendItem
CollapseAllChildren
Delete
DeleteChildren
EnsureVisible
IsVisible

Expand
Collapse

GetItemData
SetItemData

GetSelection


ItemHasChildren
SetItemHasChildren


EVT_TREE_ITEM_COLLAPSING
EVT_TREE_ITEM_EXPANDING
EVT_TREE_ITEM_MENU
EVT_TREE_ITEM_ACTIVATED