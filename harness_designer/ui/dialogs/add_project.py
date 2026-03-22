from typing import TYPE_CHECKING

import wx
import os

from ..widgets import text_ctrl as _text_ctrl
from ... import config as _config
from . import dialog_base as _dialog_base

if TYPE_CHECKING:
    from ...database.project_db import project as _project


Config = _config.Config

FILE_WILDCARD = (
    "All Supported Models |*.3mf;*.glTF;*.igs;*.iges;*.dae;*.obj;*.stp;*.step;"
    "*.stl;*.vrml;*.wrl;*.mdl;*.hmp;*.3ds;*.ase;*.ac;*.ac3d;*.dxf;*.bvh;*.blend;"
    "*.csm;*.x;*.md5mesh;*.md5anim;*.md5camera;*.fbx;*.ifc;*.irr;*.irrmesh;*.lwo;"
    "*.lws;*.ms3d;*.lxo;*.nff;*.off;*.mesh.xml;*.skeleton.xml;*.ogex;*.mdl;*.md2;"
    "*.md3;*.pk3;*.q3o;*.q3s;*.raw;*.mdc;*.ply;*.ter;*.cob;*.scn;*.smd;*.vta;*.xgl;"
    "*.amf;*.assbin;*.b3d;*.iqm;*.ndo;*.q3d;*.sib;*.x3d;*.x3db;*.x3dz;*.x3dbz;"
    "*.pmd;*.pmx|"
    "All Files |*.*|"
    "3MF (3mf)|*.3mf|"
    "glTF (glTF)|*.glTF|"
    "IGES (igs; iges)|*.igs;*.iges|"
    "Collada (dae)|*.dae|"
    "Wavefront Object (obj)|*.obj|"
    "STEP (stp; step)|*.stp;*.step|"
    "STL (stl)|*.stl|"
    "VRML (vrml; wrl)|*.vrml;*.wrl|"
    "3D GameStudio (mdl; hmp)|*.mdl;*.hmp|"
    "3D Studio Max (3ds; ase)|*.3ds;*.ase|"
    "AC3D (ac; ac3d)|*.ac;*.ac3d|"
    "Autodesk/AutoCAD DXF (dxf)|*.dxf|"
    "Biovision BVH (bvh)|*.bvh|"
    "Blender BVH (blend)|*.blend|"
    "CharacterStudio Motion (csm)|*.csm|"
    "DirectX X (x)|*.x|"
    "Doom 3 (md5mesh; md5anim; md5camera)|*.md5mesh;*.md5anim;*.md5camera|"
    "FBX-Format (fbx)|*.fbx|"
    "IFC-STEP (ifc)|*.ifc|"
    "Irrlicht Mesh/Scene (irr; irrmesh)|*.irr;*.irrmesh|"
    "LightWave Model/Scene (lwo; lws)|*.lwo;*.lws|"
    "Milkshape 3D (ms3d)|*.ms3d|"
    "Modo Model (lxo)|*.lxo|"
    "Neutral File Format (nff)|*.nff|"
    "Object File Format (off)|*.off|"
    "Ogre (mesh.xml; skeleton.xml)|*.mesh.xml;*.skeleton.xml|"
    "OpenGEX-Fomat (ogex)|*.ogex|"
    "Quake I/II/III/3BSP (mdl; md2; md3; pk3)|*.mdl;*.md2;*.md3;*.pk3|"
    "Quick3D (q3o; q3s)|*.q3o;*.q3s|"
    "Raw Triangles (raw)|*.raw|"
    "RtCW (mdc)|*.mdc|"
    "Sense8 WorldToolkit (nff)|*.nff|"
    "Polygon File Format (ply)|*.ply|"
    "Stanford Triangle Format (ply)|*.ply|"
    "Terragen Terrain (ter)|*.ter|"
    "TrueSpace (cob; scn)|*.cob;*.scn|"
    "Valve Model (smd; vta)|*.smd;*.vta|"
    "XGL-3D-Format (xgl)|*.xgl|"
    "Additive Manufacturing (amf)|*.amf|"
    "ASSBIN (assbin)|*.assbin|"
    "OpenBVE 3D (b3d)|*.b3d|"
    "Inter-Quake Model (iqm)|*.iqm|"
    "3D Low-polygon Modeler (ndo)|*.ndo|"
    "Quest3D (q3d)|*.q3d|"
    "Silo Model Format (sib)|*.sib|"
    "Extensible 3D (x3d; x3db; x3dz; x3dbz)|*.x3d;*.x3db;*.x3dz;*.x3dbz|"
    "MikuMikuDance Format (pmd; pmx)|*.pmd;*.pmx"
)


class AddProjectDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, table: "_project.ProjectsTable"):
        self.table = table

        _dialog_base.BaseDialog.__init__(self, parent, 'Project', 'Add Project', size=(-1, 475))

        width, height = self.GetTextExtent('Open File')
        height = int(height * 2.5)

        self.name_ctrl = _text_ctrl.TextCtrl(self.panel, 'Project Name:', (-1, int(height / 1.5)), apply_button=False, hslider=False)
        self.creator_ctrl = _text_ctrl.TextCtrl(self.panel, 'Creator:', (-1, int(height / 1.5)), apply_button=False, hslider=False)
        self.desc_ctrl = _text_ctrl.TextCtrl(self.panel, 'Description:', (-1, height * 4), style=wx.TE_MULTILINE, apply_button=False)
        self.user_model_ctrl = _text_ctrl.TextCtrl(self.panel, 'User Model:', (-1, height), apply_button=False)
        self.user_model_button = wx.Button(self.panel, wx.ID_ANY, label='Open File', size=(-1, -1))

        self.user_model_ctrl.ctrl.AutoCompleteDirectories()
        self.user_model_ctrl.ctrl.AutoCompleteFileNames()

        self.user_model_ctrl.Bind(wx.EVT_TEXT, self.on_user_model_text)
        self.user_model_button.Bind(wx.EVT_BUTTON, self.on_open_file)
        self.name_ctrl.Bind(wx.EVT_TEXT, self.on_name_text)
        self.name_ctrl.SetValue(name)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.user_model_ctrl, 1, wx.RIGHT, 10)
        hsizer.Add(self.user_model_button, 0, wx.ALIGN_CENTER)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.name_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        vsizer.Add(self.creator_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        vsizer.Add(self.desc_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        vsizer.Add(hsizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        self.panel.SetSizer(vsizer)
        self.Layout()

    def GetValue(self):
        return (
            self.name_ctrl.GetValue(),
            self.creator_ctrl.GetValue(),
            self.desc_ctrl.GetValue(),
            self.user_model_ctrl.GetValue()
        )

    def on_name_text(self, evt):
        def _do():
            name = self.name_ctrl.GetValue()

            try:
                _ = self.table[name]
                attr = wx.TextAttr(wx.Colour(255, 0, 0, 255))
            except KeyError:
                attr = wx.TextAttr(wx.Colour(0, 0, 0, 255))

            self.name_ctrl.ctrl.SetStyle(0, self.name_ctrl.ctrl.GetLastPosition(), attr)

        wx.CallAfter(_do)
        evt.Skip()

    def on_user_model_text(self, evt):
        def _do():
            path = self.user_model_ctrl.GetValue()
            if os.path.isfile(path):
                attr = wx.TextAttr(wx.Colour(0, 0, 0, 255))
            else:
                attr = wx.TextAttr(wx.Colour(255, 0, 0, 255))

            self.user_model_ctrl.ctrl.SetStyle(0, self.user_model_ctrl.ctrl.GetLastPosition(), attr)

        wx.CallAfter(_do)
        evt.Skip()

    def on_open_file(self, evt):
        try:
            wx.SystemOptions.SetOption(wx.OSX_FILEDIALOG_ALWAYS_SHOW_TYPES, 1)  # NOQA
        except (AttributeError, NameError):
            pass

        path = self.user_model_ctrl.GetValue()
        if path:
            default_dir, default_file = os.path.split(path)
        else:
            default_dir = Config.project.model_dir
            default_file = ''

        dlg = wx.FileDialog(
            self, message="Choose a model",
            defaultDir=default_dir,
            defaultFile=default_file,
            wildcard=FILE_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW | wx.FD_SHOW_HIDDEN
        )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            Config.project.model_dir = os.path.split(path)[0]
            self.user_model_ctrl.SetValue(path)

        dlg.Destroy()

        evt.Skip()
