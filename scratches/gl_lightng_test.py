import wx
import sys


try:
    from wx import glcanvas


    haveGLCanvas = True
except ImportError:
    haveGLCanvas = False

try:
    # The Python OpenGL package can be found at
    # http://PyOpenGL.sourceforge.net/
    from OpenGL.GL import *
    from OpenGL.GLUT import *


    haveOpenGL = True
except ImportError:
    haveOpenGL = False

# ----------------------------------------------------------------------

buttonDefs = {
    wx.NewId(): ('CubeCanvas', 'Cube'),
    wx.NewId(): ('ConeCanvas', 'Cone'),
}


class ButtonPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add((20, 30))
        keys = list(buttonDefs.keys())
        keys.sort()
        for k in keys:
            text = buttonDefs[k][1]
            btn = wx.Button(self, k, text)
            box.Add(btn, 0, wx.ALIGN_CENTER | wx.ALL, 15)
            self.Bind(wx.EVT_BUTTON, self.OnButton, btn)

        # ** Enable this to show putting a GLCanvas on the wx.Panel
        if 0:  # setting to 1 doesn't seem to do anything
            c = CubeCanvas(self)
            c.SetSize((200, 200))
            box.Add(c, 0, wx.ALIGN_CENTER | wx.ALL, 15)

        self.SetAutoLayout(True)
        self.SetSizer(box)

    def OnButton(self, evt):
        if not haveGLCanvas:
            dlg = wx.MessageDialog(
                self,
                'The GLCanvas class has not been included with this build of wxPython!',
                'Sorry',
                wx.OK | wx.ICON_WARNING
                )
            dlg.ShowModal()
            dlg.Destroy()

        elif not haveOpenGL:
            dlg = wx.MessageDialog(
                self,
                'The OpenGL package was not found.  You can get it at\n'
                'http://PyOpenGL.sourceforge.net/',
                'Sorry',
                wx.OK | wx.ICON_WARNING
                )
            dlg.ShowModal()
            dlg.Destroy()

        else:
            canvasClassName = buttonDefs[evt.GetId()][0]
            canvasClass = eval(canvasClassName)
            cx = 0
            if canvasClassName == 'ConeCanvas':
                cx = 400
            frame = Test(canvasClass)
            frame.Show(True)

            frame.SendSizeEvent()


class CanvasPanel(wx.Panel):

    def __init__(self, parent, canvasClass):
        w, h = parent.GetClientSize()

        wx.Panel.__init__(
            self,
            parent,
            wx.ID_ANY,
            style=wx.BORDER_NONE,
            size=(w, int(h / 2.5))
            )
        self.canvas = canvasClass(self, parent)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.canvas, 0, wx.EXPAND)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        self.SetSizer(vsizer)


class HSizer(wx.BoxSizer):

    def __init__(self, parent, *args):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        for arg in args:
            if isinstance(arg, str):
                st = wx.StaticText(parent, wx.ID_ANY, label=arg)
                self.Add(st, 0, wx.ALL, 5)
            elif arg is None:
                self.AddSpacer(1)
            else:
                self.Add(arg, 0, wx.ALL, 5)


class Test(wx.Frame):

    def __init__(self, canvasClass):
        wx.Frame.__init__(self, None, wx.ID_ANY, size=(600, 1000))
        self.cp = CanvasPanel(self, canvasClass)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.cp, 0)

        def on_amaterial(evt):
            self.amb_material = [item.GetValue() / 255.0 for item in (
            amaterial_r, amaterial_g, amaterial_b, amaterial_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        amaterial_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        amaterial_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        amaterial_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        amaterial_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (amaterial_r, amaterial_g, amaterial_b, amaterial_a):
            item.Bind(wx.EVT_SPINCTRL, on_amaterial)

        s1 = HSizer(self, 'amb mat red:', amaterial_r)
        s2 = HSizer(self, 'amb mat grn:', amaterial_g)
        s3 = HSizer(self, 'amb mat blu:', amaterial_b)
        s4 = HSizer(self, 'amb mat alp:', amaterial_a)

        def on_dmaterial(evt):
            self.dif_material = [item.GetValue() / 255.0 for item in (
            dmaterial_r, dmaterial_g, dmaterial_b, dmaterial_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        dmaterial_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='204',
            initial=204,
            min=0,
            max=255
            )
        dmaterial_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='204',
            initial=204,
            min=0,
            max=255
            )
        dmaterial_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='204',
            initial=204,
            min=0,
            max=255
            )
        dmaterial_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (dmaterial_r, dmaterial_g, dmaterial_b, dmaterial_a):
            item.Bind(wx.EVT_SPINCTRL, on_dmaterial)

        s5 = HSizer(self, 'dif mat red:', dmaterial_r)
        s6 = HSizer(self, 'dif mat grn:', dmaterial_g)
        s7 = HSizer(self, 'dif mat blu:', dmaterial_b)
        s8 = HSizer(self, 'dif mat alp:', dmaterial_a)

        def on_smaterial(evt):
            self.spec_material = [item.GetValue() / 255.0 for item in (
            smaterial_r, smaterial_g, smaterial_b, smaterial_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        smaterial_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        smaterial_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='0',
            initial=0,
            min=0,
            max=255
            )
        smaterial_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        smaterial_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (smaterial_r, smaterial_g, smaterial_b, smaterial_a):
            item.Bind(wx.EVT_SPINCTRL, on_smaterial)

        s9 = HSizer(self, 'spec mat red:', smaterial_r)
        s10 = HSizer(self, 'spec mat grn:', smaterial_g)
        s11 = HSizer(self, 'spec mat blu:', smaterial_b)
        s12 = HSizer(self, 'spec mat alp:', smaterial_a)

        s1 = HSizer(self, s1, None, s5, None, s9)
        s2 = HSizer(self, s2, None, s6, None, s10)
        s3 = HSizer(self, s3, None, s7, None, s11)
        s4 = HSizer(self, s4, None, s8, None, s12)

        sizer.Add(s1, 0)
        sizer.Add(s2, 0)
        sizer.Add(s3, 0)
        sizer.Add(s4, 0)

        self.amb_material = [0.2, 0.2, 0.2, 1.0]
        self.dif_material = [0.8, 0.8, 0.8, 1.0]
        self.spec_material = [1.0, 0.0, 1.0, 1.0]

        def on_alight(evt):
            self.amb_light = [item.GetValue() / 255.0 for item in
                              (alight_r, alight_g, alight_b, alight_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        alight_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='0',
            initial=0,
            min=0,
            max=255
            )
        alight_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        alight_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='0',
            initial=0,
            min=0,
            max=255
            )
        alight_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (alight_r, alight_g, alight_b, alight_a):
            item.Bind(wx.EVT_SPINCTRL, on_alight)

        s1 = HSizer(self, 'amb light red:', alight_r)
        s2 = HSizer(self, 'amb light grn:', alight_g)
        s3 = HSizer(self, 'amb light blu:', alight_b)
        s4 = HSizer(self, 'amb light alp:', alight_a)

        def on_dlight(evt):
            self.dif_light = [item.GetValue() / 255.0 for item in
                              (dlight_r, dlight_g, dlight_b, dlight_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        dlight_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        dlight_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        dlight_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        dlight_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (dlight_r, dlight_g, dlight_b, dlight_a):
            item.Bind(wx.EVT_SPINCTRL, on_dlight)

        s5 = HSizer(self, 'dif light red:', dlight_r)
        s6 = HSizer(self, 'dif light grn:', dlight_g)
        s7 = HSizer(self, 'dif light blu:', dlight_b)
        s8 = HSizer(self, 'dif light alp:', dlight_a)

        def on_slight(evt):
            self.spec_light = [item.GetValue() / 255.0 for item in
                               (slight_r, slight_g, slight_b, slight_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        slight_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        slight_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        slight_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )
        slight_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (slight_r, slight_g, slight_b, slight_a):
            item.Bind(wx.EVT_SPINCTRL, on_slight)

        s9 = HSizer(self, 'spec light red:', slight_r)
        s10 = HSizer(self, 'spec light grn:', slight_g)
        s11 = HSizer(self, 'spec light blu:', slight_b)
        s12 = HSizer(self, 'spec light alp:', slight_a)

        s1 = HSizer(self, s1, None, s5, None, s9)
        s2 = HSizer(self, s2, None, s6, None, s10)
        s3 = HSizer(self, s3, None, s7, None, s11)
        s4 = HSizer(self, s4, None, s8, None, s12)

        sizer.Add(s1, 0)
        sizer.Add(s2, 0)
        sizer.Add(s3, 0)
        sizer.Add(s4, 0)

        def on_mlight(evt):
            self.light_model = [item.GetValue() / 255.0 for item in
                                (mlight_r, mlight_g, mlight_b, mlight_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        mlight_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        mlight_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        mlight_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        mlight_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        for item in (mlight_r, mlight_g, mlight_b, mlight_a):
            item.Bind(wx.EVT_SPINCTRL, on_mlight)

        s1 = HSizer(self, 'mdl light red:', mlight_r)
        s2 = HSizer(self, 'mdl light grn:', mlight_g)
        s3 = HSizer(self, 'mdl light blu:', mlight_b)
        s4 = HSizer(self, 'mdl light alp:', mlight_a)

        def on_lightpos(evt):
            self.light_pos = [item.GetValue() / 100.0 for item in
                              (light_x, light_y, light_z, light_unknown)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        light_x = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='100',
            initial=100,
            min=-100,
            max=100
            )
        light_y = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='100',
            initial=100,
            min=-100,
            max=100
            )
        light_z = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='100',
            initial=100,
            min=-100,
            max=100
            )
        light_unknown = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='0',
            initial=0,
            min=-100,
            max=100
            )

        for item in (light_x, light_y, light_z, light_unknown):
            item.Bind(wx.EVT_SPINCTRL, on_lightpos)

        s5 = HSizer(self, 'light pos x:', light_x)
        s6 = HSizer(self, 'light pos y:', light_y)
        s7 = HSizer(self, 'light pos z:', light_z)
        s8 = HSizer(self, 'light pos ?:', light_unknown)

        self.amb_light = [0.0, 1.0, 0.0, 1.0]
        self.dif_light = [1.0, 1.0, 1.0, 1.0]
        self.spec_light = [1.0, 1.0, 1.0, 1.0]
        self.light_pos = [1.0, 1.0, 1.0, 0.0]
        self.light_model = [0.2, 0.2, 0.2, 1.0]

        def on_cc(evt):
            self.cc = [item.GetValue() / 255.0 for item in
                       (cc_r, cc_g, cc_b, cc_a)]
            self.cp.canvas.Refresh(False)
            evt.Skip()

        cc_r = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        cc_g = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        cc_b = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='51',
            initial=51,
            min=0,
            max=255
            )
        cc_a = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='255',
            initial=255,
            min=0,
            max=255
            )

        self.cc = [0.2, 0.2, 0.2, 1.0]

        for item in (cc_r, cc_g, cc_b, cc_a):
            item.Bind(wx.EVT_SPINCTRL, on_cc)

        s9 = HSizer(self, 'cc red:', cc_r)
        s10 = HSizer(self, 'cc grn:', cc_g)
        s11 = HSizer(self, 'cc blu:', cc_b)
        s12 = HSizer(self, 'cc alp:', cc_a)

        s1 = HSizer(self, s1, None, s5, None, s9)
        s2 = HSizer(self, s2, None, s6, None, s10)
        s3 = HSizer(self, s3, None, s7, None, s11)
        s4 = HSizer(self, s4, None, s8, None, s12)

        sizer.Add(s1, 0)
        sizer.Add(s2, 0)
        sizer.Add(s3, 0)
        sizer.Add(s4, 0)

        def on_shine(evt):
            self.shine = float(shine.GetValue())
            evt.Skip()

        shine = wx.SpinCtrl(
            self,
            wx.ID_ANY,
            value='50',
            initial=50,
            min=-255,
            max=255
            )
        shine.Bind(wx.EVT_SPINCTRL, on_shine)

        self.shine = 50.0

        s1 = HSizer(self, 'shine:', shine)
        sizer.Add(s1, 0)

        self.SetSizer(sizer)


class MyCanvasBase(glcanvas.GLCanvas):

    def __init__(self, parent, frm: "Test"):
        self.frame = frm

        w, h = self.frame.GetClientSize()

        glcanvas.GLCanvas.__init__(self, parent, -1, size=(w, int(h / 2.5)))
        self.init = False
        self.context = glcanvas.GLContext(self)

        # initial mouse position
        self.lastx = self.x = 30
        self.lasty = self.y = 30
        self.size = None
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)

    def OnEraseBackground(self, event):
        pass  # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        print('size_event')
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetSize()

        print(*size)
        self.SetCurrent(self.context)
        glViewport(0, 0, size.width, size.height)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.context)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

    def OnMouseDown(self, evt):
        self.CaptureMouse()
        self.x, self.y = self.lastx, self.lasty = evt.GetPosition()

    def OnMouseUp(self, evt):
        self.ReleaseMouse()

    def OnMouseMotion(self, evt):
        if evt.Dragging() and evt.LeftIsDown():
            self.lastx, self.lasty = self.x, self.y
            self.x, self.y = evt.GetPosition()
            self.Refresh(False)


class CubeCanvas(MyCanvasBase):

    def InitGL(self):

        print('gl init')
        # set viewing projection
        glMatrixMode(GL_PROJECTION)
        glFrustum(-0.5, 0.5, -0.5, 0.5, 1.0, 3.0)

        # position viewer
        glMatrixMode(GL_MODELVIEW)
        glTranslatef(0.0, 0.0, -2.0)

        # position object
        glRotatef(self.y, 1.0, 0.0, 0.0)
        glRotatef(self.x, 0.0, 1.0, 0.0)
        glLight(
            GL_LIGHT0,
            GL_POSITION,
            (5, 5, 5, 1)
        )  # point light from the left, top, front
        glEnable(GL_DEPTH_TEST)

    def OnDraw(self):
        # clear color and depth buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glEnable(GL_LIGHTING)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_LIGHT0)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glMaterialfv(GL_FRONT, GL_AMBIENT, self.frame.amb_material)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, self.frame.dif_material)
        glMaterialfv(GL_FRONT, GL_SPECULAR, self.frame.spec_material)
        glMaterialf(GL_FRONT, GL_SHININESS, self.frame.shine)

        glLightfv(GL_LIGHT0, GL_AMBIENT, self.frame.amb_light)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, self.frame.dif_light)
        glLightfv(GL_LIGHT0, GL_SPECULAR, self.frame.spec_light)
        glLightfv(GL_LIGHT0, GL_POSITION, self.frame.light_pos)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, self.frame.light_model)

        # draw six faces of a cube
        glBegin(GL_QUADS)
        glNormal3f(0.0, 0.0, 1.0)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)

        glNormal3f(0.0, 0.0, -1.0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)

        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(-0.5, 0.5, 0.5)

        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(-0.5, -0.5, 0.5)

        glNormal3f(1.0, 0.0, 0.0)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)

        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glEnd()

        if self.size is None:
            self.size = self.GetClientSize()
        w, h = self.size
        w = max(w, 1.0)
        h = max(h, 1.0)
        xScale = 180.0 / w
        yScale = 180.0 / h
        glRotatef((self.y - self.lasty) * yScale, 1.0, 0.0, 0.0)
        glRotatef((self.x - self.lastx) * xScale, 0.0, 1.0, 0.0)

        glDisable(GL_LIGHT0)
        glDisable(GL_LIGHTING)
        glDisable(GL_COLOR_MATERIAL)

        self.SwapBuffers()


class ConeCanvas(MyCanvasBase):

    def InitGL(self):
        glMatrixMode(GL_PROJECTION)
        # camera frustrum setup
        glFrustum(-0.5, 0.5, -0.5, 0.5, 1.0, 3.0)
        glMaterial(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glMaterial(GL_FRONT, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glMaterial(GL_FRONT, GL_SPECULAR, [1.0, 0.0, 1.0, 1.0])
        glMaterial(GL_FRONT, GL_SHININESS, 50.0)

        glLight(GL_LIGHT0, GL_AMBIENT, [0.0, 1.0, 0.0, 1.0])
        glLight(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLight(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glLight(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # position viewer
        glMatrixMode(GL_MODELVIEW)
        # position viewer
        glTranslatef(0.0, 0.0, -2.0);
        #
        glutInit(sys.argv)

    def OnDraw(self):
        # clear color and depth buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # use a fresh transformation matrix
        glPushMatrix()
        # position object
        # glTranslate(0.0, 0.0, -2.0)
        glRotate(30.0, 1.0, 0.0, 0.0)
        glRotate(30.0, 0.0, 1.0, 0.0)

        glTranslate(0, -1, 0)
        glRotate(250, 1, 0, 0)
        glutSolidCone(0.5, 1, 30, 5)
        glPopMatrix()
        glRotatef((self.y - self.lasty), 0.0, 0.0, 1.0);
        glRotatef((self.x - self.lastx), 1.0, 0.0, 0.0);
        # push into visible buffer
        self.SwapBuffers()


# ----------------------------------------------------------------------
class RunDemoApp(wx.App):

    def __init__(self):
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        frame = wx.Frame(
            None, -1, "RunDemo: ", pos=(0, 0),
            style=wx.DEFAULT_FRAME_STYLE, name="run a sample"
            )
        # frame.CreateStatusBar()

        menuBar = wx.MenuBar()
        menu = wx.Menu()
        item = menu.Append(wx.ID_EXIT, "E&xit\tCtrl-Q", "Exit demo")
        self.Bind(wx.EVT_MENU, self.OnExitApp, item)
        menuBar.Append(menu, "&File")

        frame.SetMenuBar(menuBar)
        frame.Show(True)
        frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)

        win = runTest(frame)

        # set the frame to a good size for showing the two buttons
        frame.SetSize((200, 250))
        win.SetFocus()
        self.window = win
        frect = frame.GetRect()

        self.SetTopWindow(frame)
        self.frame = frame
        return True

    def OnExitApp(self, evt):
        self.frame.Close(True)

    def OnCloseFrame(self, evt):
        if hasattr(self, "window") and hasattr(self.window, "ShutdownDemo"):
            self.window.ShutdownDemo()
        evt.Skip()


def runTest(frame):
    win = ButtonPanel(frame)
    return win


app = RunDemoApp()
app.MainLoop()
