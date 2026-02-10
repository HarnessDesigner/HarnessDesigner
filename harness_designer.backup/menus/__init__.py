import wx

from .. import Config

class ProjectMenu(wx.Menu):

    def __init__(self, mainframe):
        super().__init__()

        self.mainframe = mainframe

        item = self.Append(wx.ID_ANY, 'New', 'Creates a new project.')
        mainframe.Bind(wx.EVT_MENU, self.on_create, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Open', 'Open a project.')
        mainframe.Bind(wx.EVT_MENU, self.on_open, id=item.GetId())

        self.recent_menu = wx.Menu()
        for item in Config.project.recent_projects:
            sm_item = self.recent_menu.Append(wx.ID_ANY, item)
            self.Bind(wx.EVT_MENU, self.on_recent, sm_item)

        self.Append(wx.ID_ANY, 'Open Recent', self.recent_menu, 'Open a recent project.')

        self.AppendSeparator()

        item = self.Append(wx.ID_ANY, 'Delete', 'Deletes a new project.')
        mainframe.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Rename', 'Renames a project.')
        mainframe.Bind(wx.EVT_MENU, self.on_rename, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Print', 'Prints the project data.')
        mainframe.Bind(wx.EVT_MENU, self.on_print, id=item.GetId())

    def on_create(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_open(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_recent(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_rename(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_print(self, evt: wx.MenuEvent):
        evt.Skip()


class EditMenu(wx.Menu):

    def __init__(self, mainframe):
        super().__init__()

        self.mainframe = mainframe

        item = self.Append(wx.ID_ANY, 'Cut', '')
        mainframe.Bind(wx.EVT_MENU, self.on_cut, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Copy', '')
        mainframe.Bind(wx.EVT_MENU, self.on_copy, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Paste', '')
        mainframe.Bind(wx.EVT_MENU, self.on_paste, id=item.GetId())

        self.AppendSeparator()

        item = self.Append(wx.ID_ANY, 'Delete Object', 'Deletes an object.')
        mainframe.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Select Object', 'Selects an object.')
        mainframe.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

    def on_cut(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_copy(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_paste(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_print(self, evt: wx.MenuEvent):
        evt.Skip()


'''

View
=================
Status Bar


3D View
Schematic View


Show/Hide    (Changes between Show and Hide)
  Hide Housings
  Hide Seals
  Hide Wires
  Hide Bundles
  Hide Covers
  Hide TPA Locks
  Hide CPA Locks
  Hide Bundles
  Hide Transitions
  Hide Terminal Pins
  Hide Notes



'''



class LightingMenu(wx.Menu):

    def __init__(self, mainframe):
        super().__init__()

        self.mainframe = mainframe

        ambient_menu = wx.Menu()
        item = ambient_menu.Append(wx.ID_ANY, 'Color', 'Set Ambient light color.')
        mainframe.Bind(wx.EVT_MENU, self.on_ambient_color, id=item.GetId())

        self.Append(wx.ID_ANY, 'Ambient', ambient_menu, 'Ambient Lighting.')

        headlight_menu = HeadlightMenu(mainframe)
        self.Append(wx.ID_ANY, 'Headlight', headlight_menu, 'Headlight Settings.')

    def on_ambient_color(self, evt: wx.MenuEvent):
        evt.Skip()



class Menu3D(wx.Menu):

    def __init__(self, mainframe):
        super().__init__()

        self.mainframe = mainframe

        item = self.Append(wx.ID_ANY, 'Cut', '')
        mainframe.Bind(wx.EVT_MENU, self.on_cut, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Copy', '')
        mainframe.Bind(wx.EVT_MENU, self.on_copy, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Paste', '')
        mainframe.Bind(wx.EVT_MENU, self.on_paste, id=item.GetId())

        self.AppendSeparator()

        item = self.Append(wx.ID_ANY, 'Delete Object', 'Deletes an object.')
        mainframe.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Select Object', 'Selects an object.')
        mainframe.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

    def on_cut(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_copy(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_paste(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_print(self, evt: wx.MenuEvent):
        evt.Skip()


class HeadlightMenu(wx.Menu):

    def __init__(self, mainframe):

        super().__init__()

        self.mainframe = mainframe

        item = self.Append(wx.ID_ANY, 'Enable', 'Turns on and off the headlight.')
        mainframe.Bind(wx.EVT_MENU, self.on_enable_disable, id=item.GetId())

        self.AppendSeparator()

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Diffuse', 'Sets the edge sharpness.')
        mainframe.Bind(wx.EVT_MENU, self.on_diffuse, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Size', 'How large in diameter the beam is.')
        mainframe.Bind(wx.EVT_MENU, self.on_size, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Color', 'Color of the light.')
        mainframe.Bind(wx.EVT_MENU, self.on_color, id=item.GetId())

    def on_enable_disable(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_diffuse(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_size(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_color(self, evt: wx.MenuEvent):
        evt.Skip()


class FloorMenu(wx.Menu):

    def __init__(self, mainframe):
        super().__init__()

        self.mainframe = mainframe

        item = self.Append(wx.ID_ANY, 'Enable', 'Turns on and off the grid.')
        mainframe.Bind(wx.EVT_MENU, self.on_enable_disable, id=item.GetId())

        self.AppendSeparator()

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Distance', 'Distance the grid is seen for from (0, 0, 0)')
        mainframe.Bind(wx.EVT_MENU, self.on_distance, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Grid Spacing', 'Size of the grid tiles.')
        mainframe.Bind(wx.EVT_MENU, self.on_spacing, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Even Color', 'Color of even numbered squares.')
        mainframe.Bind(wx.EVT_MENU, self.on_even_color, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Odd Color', 'Color of odd numbered squares.')
        mainframe.Bind(wx.EVT_MENU, self.on_odd_color, id=item.GetId())

    def on_enable_disable(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_distance(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_spacing(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_even_color(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_odd_color(self, evt: wx.MenuEvent):
        evt.Skip()


class GridMenu(wx.Menu):

    def __init__(self, mainframe):
        super().__init__()

        self.mainframe = mainframe

        item = self.Append(wx.ID_ANY, 'Enable', 'Turns on and off the grid.')
        mainframe.Bind(wx.EVT_MENU, self.on_enable_disable, id=item.GetId())

        self.AppendSeparator()

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Distance', 'Distance the grid is seen for from (0, 0, 0)')
        mainframe.Bind(wx.EVT_MENU, self.on_distance, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Grid Spacing', 'Size of the grid tiles.')
        mainframe.Bind(wx.EVT_MENU, self.on_spacing, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Even Color', 'Color of even numbered squares.')
        mainframe.Bind(wx.EVT_MENU, self.on_even_color, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Odd Color', 'Color of odd numbered squares.')
        mainframe.Bind(wx.EVT_MENU, self.on_odd_color, id=item.GetId())

    def on_enable_disable(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_distance(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_spacing(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_even_color(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_odd_color(self, evt: wx.MenuEvent):
        evt.Skip()


Camera



'''

3D
=================
Lighting
  Ambient
    Color    (open color picker dialog

  Headlight
    Enable     (Changes between Enable and Disable)
    Diffuse    (popup window with slider and manual entry)
    Size     (popup window with slider and manual entry)
    Color    (open color picker dialog)


Floor
  Enable    (Changes between Enable and Disable)
  Height    (popup window with slider and manual entry)

  Grid
    Enable    (changes between Enable and Disable)
    Distance     (popup window with slider and manual entry)
    Grid Spacing  (popup window with slider and manual entry)
    Second Color   (color picker dialog)



Pan Camera
  Left
  Right
Tilt Camera
  Up
  Down
Truck Camera
  Left
  Right
Dolly Camera
  Forward
  Backward
Pedestal Camera
  Up
  Down
Rotate Camera
  Left
  Right
  Up
  Down
Zoom Camera
  In
  Out

Camera Focal Point
  Enable    (Changes between Enable and Disable)
  Size     (popup window with slider and manual entry)




Tools
=================
Design Rules   (dialog)
Circuit Design    (dialog)

Time Tracker    (aui pane)
Python Console   (aui pane)
Part Scrapers    (aui pane)
Python Scripting    (aui pane)
Create BOM        (aui pane)
Assembly Weight    ()
Screen Capture



Settings
=================


Schematic Editor
----------------
  Snap Settings
  Grid Settings
  Cursor Settings


3D Editor
----------------
  Snap Settings
  -------------------
  Show Axis Indicator
  -------------------
  Mouse Settings   (dialog)
  Keyboard Settings   (dialog)





Window
=================
Show 3D Orientation Window
Show Schematic Editor
Show 3D Editor
Show Concentric Twist Editor

Show Parts Database Editor
Show Project Database Editor
Show Object Attributes Panel
Show Datasheet Viewer

Show 3D Preview
Show Part Image Preview


Show 3D Toolbar
Show Schematic Toolbar

Reset 3D Editor View
Reset Schematic Editor View


Tile Horizontally   (reparent tabs into their own panes)
Tile Vertically     (reparent tabs into their own panes)
Tab Editors         (reparent panes into tabs)



Help
=================
About   (dialog)



'''