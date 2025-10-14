import wx
from wx.lib.agw import aui
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

        self.manager.AddPane
        self.manager.LoadPaneInfo
        self.manager.LoadPerspective

        self.manager.SavePaneInfo
        self.manager.SavePerspective

        self.manager.Update

        self.editor_notebook = aui.AuiNotebook(self, wx.ID_ANY,
                                        agwStyle=aui.AUI_NB_TOP |
                                                 aui.AUI_NB_TAB_MOVE |
                                                 aui.AUI_NB_TAB_EXTERNAL_MOVE |
                                                 aui.AUI_NB_DRAW_DND_TAB |
                                                 aui.AUI_NB_TAB_FLOAT)

        self.editor = _editor.Editor(self.editor_notebook)

        self.editor_notebook.AddPage(self.editor, '3D View')

        self.schematic = _schematic.Schemaitc(self.editor_notebook)
        self.editor_notebook.AddPage(self.schematic, 'Schematic View')


        self.attributes_notebook = aui.AuiNotebook(self, wx.ID_ANY,
                                        agwStyle=aui.AUI_NB_BOTTOM |
                                                 aui.AUI_NB_TAB_MOVE |
                                                 aui.AUI_NB_TAB_EXTERNAL_MOVE |
                                                 aui.AUI_NB_DRAW_DND_TAB |
                                                 aui.AUI_NB_TAB_FLOAT)

        self.manager.SetManagedWindow(self)

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

    WireAttrPanel
    TransAttrPanel
    TerminalAttrPanel
    SpliceAttrPanel
    HousingAttrPanel
    ConnectorAttrPanel
    BundleAttrPanel
    CavityAttrPanel
    MfgAttrPanel
    BootAttrPanel
    CoverAttrPanel
    CPALockAttrPanel
    TPALockAttrPanel
    SealAttrPanel


    CavityViewPanel
    SchematicViewPanel
    HTMLViewPanel
    PythonViewPanel



    def AddTransAttrPage(self):
        RemovePage





        .Caption()

        AuiPaneInfo
        Bottom()

        Left()
        Right()
        Top()

        CenterPane()
        ToolbarPane()

        Dockable()
        Floatable()
        Resizable()




        Hide()
        Show()
        IsShown()



        CloseButton()
        MaximizeButton()
        MinimizeButton()
        PinButton()





        aui.


AuiNotebook






AuiToolBar
AuiToolBarItem



class App(wx.App):
    def OnInit(self):
        frame = Frame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = App()
    app.MainLoop()