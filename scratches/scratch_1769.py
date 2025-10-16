import wx
import cv2
import wx.lib.buttons


ecm_pin_layer = r'C:\Users\drsch\Desktop\HarnessMaker\ecm_x2_pin_layer.png'
ecm = r'C:\Users\drsch\Desktop\HarnessMaker\exm_x2.png'

app = wx.App()


class ButtonDialog(wx.Dialog):
    def __init__(self, name, size, terminal, circuit):

        wx.Dialog.__init__(self, None, title='Cavity Parameters', size=(300, 400), style=wx.CAPTION | wx.RESIZE_BORDER | wx.CLOSE_BOX | wx.STAY_ON_TOP)
        self.Centre()

        sizer = wx.BoxSizer(wx.VERTICAL)
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, label="Name:")
        self.name_ctrl = wx.TextCtrl(self, value=name, size=(50, -1))

        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.name_ctrl, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, "Size:")
        self.size_ctrl = wx.SpinCtrlDouble(self, value=str(size), size=(75, -1), min=0.5, max=10.0, inc=0.05)
        self.size_ctrl.SetDigits(2)

        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.size_ctrl, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, "Terminal:")
        self.terminal_ctrl = wx.TextCtrl(self, value=terminal, size=(75, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.terminal_ctrl, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, "Circuit:")
        self.circuit_ctrl = wx.TextCtrl(self, value=circuit, size=(75, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.circuit_ctrl, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.EXPAND | wx.RIGHT | wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddStretchSpacer(1)
        btn = wx.Button(self, wx.ID_OK, label='Save')
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()

    def GetValues(self):
        return (
            self.name_ctrl.GetValue(),
            self.size_ctrl.GetValue(),
            self.terminal_ctrl.GetValue(),
            self.circuit_ctrl.GetValue()
        )


def get_cavities(filename):
    res = []

    # read the image of rectangle as grayscale
    img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)

    # threshold
    thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # compute largest contour
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.001 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            res.insert(0, (x, y, w, h))

    return res


class CavityButton(wx.lib.buttons.GenButton):
    def __init__(self, parent, id, name, pos, size, circuit, cavity_size, terminal, color):
        wx.lib.buttons.GenButton.__init__(self, parent, pos=pos, style=wx.BORDER_SUNKEN, size=size, name=name)
        self.SetBackgroundColour(wx.Colour(*color))
        self.SetForegroundColour(wx.Colour(0, 0, 0, 255))
        self.SetMinSize(size)
        self.SetMaxSize(size)

        self._size = cavity_size
        self._terminal = terminal
        self._circuit = circuit
        self._id = id

        self.SetLabel(name)
        self.SetToolTip()
        
        self.Bind(wx.EVT_BUTTON, self._on_button)

    def _on_button(self, evt):
        dlg = ButtonDialog(self.GetLabel(), self._size, self._terminal, self._circuit)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                name, self._size, self._terminal, self._circuit = dlg.GetValues()
                self.SetLabel(name)
                self.SetToolTip()
        finally:
            dlg.Destroy()

        evt.Skip()

    def GetId(self):
        return self._id

    def GetColour(self):
        return self.GetBackgroundColour()

    def SetColour(self, value):
        self.SetBackgroundColour(value)

    def GetCircuit(self):
        return self._circuit

    def SetCircuit(self, value):
        self._circuit = value
        self.SetToolTip()

    def GetTerminal(self):
        return self._terminal

    def SetTerminal(self, value):
        self._terminal = value
        self.SetToolTip()

    def GetName(self):
        return self.GetLabel()

    def SetName(self, value):
        self.SetLabel(value)
        self.SetToolTip()

    def GetSize(self):
        return self._size

    def SetSize(self, value):
        self._size = value
        self.SetToolTip()

    def SetToolTip(self):  # NOQA
        tt = [
            f'ID:       {self.GetId()}',
            f'Name:     {self.GetName()}',
            f'Circuit:  {self.GetCircuit()}',
            f'Terminal: {self.GetTerminal()}',
            f'Size:     {self.GetSize()}'
        ]

        wx.Panel.SetToolTip(self, '\n'.join(tt))


class Panel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.BORDER_NONE)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.Bind(wx.EVT_DROP_FILES, self.on_drop_files)

        # self.bmp = wx.Bitmap(ecm, type=wx.BITMAP_TYPE_PNG)
        # self.bmp_overlay = wx.Bitmap(ecm_pin_layer, type=wx.BITMAP_TYPE_PNG)

        self.bmp = wx.NullBitmap
        self.bmp_overlay = wx.NullBitmap
        self.cavities = []
        self._moving_cavity = None

        self.DragAcceptFiles(True)

    def on_drop_files(self, evt):
        files = evt.GetFiles()

        for file in files:
            if file.endswith('.png'):
                type_ = wx.BITMAP_TYPE_PNG
            elif file.endswith('.bmp'):
                type_ = wx.BITMAP_TYPE_BMP
            elif file.endswith('.tif'):
                type_ = wx.BITMAP_TYPE_TIF
            elif file.endswith('.tiff'):
                type_ = wx.BITMAP_TYPE_TIFF
            elif file.endswith('.jpg'):
                type_ = wx.BITMAP_TYPE_JPEG
            elif file.endswith('.jpeg'):
                type_ = wx.BITMAP_TYPE_JPEG
            elif file.endswith('.gif'):
                type_ = wx.BITMAP_TYPE_GIF
            else:
                continue

            bmp = wx.Bitmap(file, type=type_)
            if not bmp.IsOk():
                continue

            if self.bmp != wx.NullBitmap:
                if self.bmp_overlay != wx.NullBitmap:
                    self.bmp.Destroy()
                    self.bmp_overlay.Destroy()
                    self.bmp = bmp
                    self.bmp_overlay = wx.NullBitmap
                else:
                    self.bmp_overlay = bmp

                    rects = get_cavities(file)
                    img = bmp.ConvertToImage()
                    cavities = []

                    colors = set()
                    for i, (x, y, w, h) in enumerate(rects):
                        center_x = int(w / 2) + x
                        center_y = int(h / 2) + y
                        color = (img.GetRed(center_x, center_y), img.GetGreen(center_x, center_y), img.GetBlue(center_x, center_y))
                        colors.add(color)
                        print(i + 1, ':', (x, y))

                        cavities.append(CavityButton(
                            self,
                            id=i + 1,
                            pos=(x, y),
                            size=(w, h),
                            color=color,
                            name=str(i + 1),
                            cavity_size=0.0,
                            terminal='',
                            circuit=''
                        ))

                    self.cavities = cavities
            else:
                self.bmp = bmp

        if self.bmp.IsOk():
            self.GetParent().SetClientSize(self.bmp.GetSize())
            self.GetParent().SetMinClientSize(self.bmp.GetSize())

        wx.CallAfter(self.Refresh)

        evt.Skip()

    def on_erase_background(self, _):
        pass

    def on_paint(self, evt):
        if self.bmp.IsOk():

            dc = wx.PaintDC(self)
            dc.Clear()

            gcdc = wx.GCDC(dc)
            gc = gcdc.GetGraphicsContext()

            gc.DrawBitmap(self.bmp, 0, 0, self.bmp.GetWidth(), self.bmp.GetHeight())

            gcdc.Destroy()
            del gcdc

        evt.Skip()


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, size=(800, 600))

        self.panel = Panel(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.panel, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.SetSizer(vsizer)
        self.Layout()

        self.Show()


frame = Frame()
app.MainLoop()


