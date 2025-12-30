from typing import TYPE_CHECKING

import wx

if TYPE_CHECKING:
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db



class ProjectExplorer(wx.TreeCtrl):

    def __init__(self, parent, g_db: "_global_db.GLBTables", p_db: "_project_db.PJTTables"):
        wx.TreeCtrl.__init__(self, parent, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_MULTIPLE)

        EVT_TREE_BEGIN_DRAG
        EVT_TREE_BEGIN_RDRAG
        EVT_TREE_END_DRAG
        EVT_TREE_BEGIN_LABEL_EDIT
        EVT_TREE_END_LABEL_EDIT
        EVT_TREE_DELETE_ITEM
        EVT_TREE_GET_INFO
        EVT_TREE_SET_INFO
        EVT_TREE_ITEM_ACTIVATED
        EVT_TREE_ITEM_COLLAPSED
        EVT_TREE_ITEM_COLLAPSING
        EVT_TREE_ITEM_EXPANDED
        EVT_TREE_ITEM_EXPANDING
        EVT_TREE_ITEM_RIGHT_CLICK
        EVT_TREE_ITEM_MIDDLE_CLICK
        EVT_TREE_SEL_CHANGED
        EVT_TREE_SEL_CHANGING
        EVT_TREE_KEY_DOWN
        EVT_TREE_ITEM_GETTOOLTIP
        EVT_TREE_ITEM_MENU










