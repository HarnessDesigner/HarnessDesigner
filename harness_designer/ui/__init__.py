import wx
from wx import aui
from . import editor as _editor


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, wx.ID_ANY, title='Harness Designer')

        aui.AUI_MGR_ALLOW_FLOATING
        aui.AUI_MGR_ALLOW_ACTIVE_PANE
        aui.AUI_MGR_TRANSPARENT_DRAG
        aui.AUI_MGR_TRANSPARENT_HINT
        aui.AUI_MGR_HINT_FADE
        aui.AUI_MGR_LIVE_RESIZE

        self.manager = aui.AuiManager()
        self.manager.SetManagedWindow(self)

        # self.manager.AddPane
        # self.manager.LoadPaneInfo
        # self.manager.LoadPerspective
        #
        # self.manager.SavePaneInfo
        # self.manager.SavePerspective
        #
        # self.manager.Update

        self.editor_notebook = aui.AuiNotebook(self, wx.ID_ANY,
                                               style=aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TOP)

        from .. import editor_3d
        from .. import editor_2d

        self.editor3d = editor_3d.Editor3D(self.editor_notebook)

        self.editor_notebook.AddPage(self.editor3d, '3D View')

        self.editor2d = editor_2d.Editor2D(self.editor_notebook)
        self.editor_notebook.AddPage(self.editor2d, 'Schematic View')


        self.attribute_notebook = aui.AuiNotebook(self, wx.ID_ANY,
                                                   style=aui.AUI_NB_TAB_MOVE | aui.AUI_NB_BOTTOM)

        self.editor_pane = (
            aui.AuiPaneInfo()
            .CenterPane()
            .Floatable(False)
            .Center()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editors')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
        )

        self.manager.AddPane(self.editor_notebook, self.editor_pane)
        self.attribute_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Center()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('attributes')
            .CaptionVisible(True)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Caption('Part Attributes')
            .Show()
        )

        self.manager.AddPane(self.attribute_notebook, self.attribute_pane)

        self.editor2d_toolbar = aui.AuiToolBar(self)

        self.editor2d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Center()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor2d_toolbar')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
            .ToolbarPane()
        )

        self.editor3d_toolbar = aui.AuiToolBar(self)

        self.editor3d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Top()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor3d_toolbar')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
            .ToolbarPane()
        )

    # WireAttrPanel
    # TransAttrPanel
    # TerminalAttrPanel
    # SpliceAttrPanel
    # HousingAttrPanel
    # ConnectorAttrPanel
    # BundleAttrPanel
    # CavityAttrPanel
    # MfgAttrPanel
    # BootAttrPanel
    # CoverAttrPanel
    # CPALockAttrPanel
    # TPALockAttrPanel
    # SealAttrPanel
    #
    #
    # CavityViewPanel
    # SchematicViewPanel
    # HTMLViewPanel
    # PythonViewPanel


class App(wx.App):
    def OnInit(self):
        frame = Frame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = App()
    app.MainLoop()