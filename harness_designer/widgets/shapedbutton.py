import wx

import PIL.Image as Image
import os

folder = os.path.split(__file__)[0]

# Import Some Stuff For The Annoying Ellipsis... ;-)
from math import sin, cos, pi


def opj(path):
    strs = os.path.join(*tuple(path.split('/')))
    # HACK: on Linux, a leading / gets lost...
    if path.startswith('/'):
        strs = '/' + strs

    return strs


class SButtonEvent(wx.CommandEvent):

    def __init__(self, eventType, eventId):
        wx.CommandEvent.__init__(self, eventType, eventId)
        self.isDown = False
        self.theButton = None

    def SetIsDown(self, isDown):
        self.isDown = isDown

    def GetIsDown(self):
        return self.isDown

    def SetButtonObj(self, btn):
        self.theButton = btn

    def GetButtonObj(self):
        return self.theButton


class SButton(wx.Window):
    _labeldelta = 1

    def __init__(self, parent, id=wx.ID_ANY, label="", pos=wx.DefaultPosition,
                 size=wx.DefaultSize):

        wx.Window.__init__(self, parent, id, pos, size)

        if label is None:
            label = ""

        self._enabled = True
        self._isup = True
        self._hasfocus = False
        self._usefocusind = True

        # Initialize Button Properties
        self.SetButtonColour()
        self.SetLabel(label)
        self.SetLabelColour()
        self.InitColours()
        self.SetAngleOfRotation()
        self.SetEllipseAxis()

        if size == wx.DefaultSize:
            self.SetInitialSize(self.DoGetBestSize())

        # Event Binding
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        if wx.Platform == '__WXMSW__':
            self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)

        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_SET_FOCUS, self.OnGainFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnLoseFocus)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda x: None)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def SetButtonColour(self, colour=None):
        if colour is None:
            colour = wx.WHITE

        palette = colour.Red(), colour.Green(), colour.Blue()

        self._buttoncolour = colour

        self._mainbuttondown = DownButton.GetImage()
        self._mainbuttonup = UpButton.GetImage()

    def GetButtonColour(self):
        return self._buttoncolour

    def SetLabelColour(self, colour=None):
        if colour is None:
            colour = wx.BLACK

        self._labelcolour = colour

    def GetLabelColour(self):
        return self._labelcolour

    def SetLabel(self, label=None):
        if label is None:
            label = ""

        self._buttonlabel = label

    def GetLabel(self):
        return self._buttonlabel

    def SetBestSize(self, size=None):
        if size is None:
            size = wx.DefaultSize

        self.SetInitialSize(size)

    def DoGetBestSize(self):
        w, h, usemin = self._GetLabelSize()
        defsize = wx.Button.GetDefaultSize()
        width = 12 + w

        if usemin and width < defsize.width:
           width = defsize.width

        height = 11 + h

        if usemin and height < defsize.height:
            height = defsize.height

        return width, height

    def AcceptsFocus(self):
        return self.IsShown() and self.IsEnabled()

    def ShouldInheritColours(self):
        return False

    def Enable(self, enable=True):
        self._enabled = enable
        self.Refresh()

    def IsEnabled(self):
        return self._enabled

    def SetUseFocusIndicator(self, flag):
        self._usefocusind = flag

    def GetUseFocusIndicator(self):
        return self._usefocusind

    def InitColours(self):
        textclr = self.GetLabelColour()
        faceclr = self.GetButtonColour()

        r, g, b, a = faceclr.Get()
        hr, hg, hb = min(255, r + 64), min(255, g + 64), min(255, b + 64)
        self._focusclr = wx.Colour(hr, hg, hb)

        if wx.Platform == "__WXMAC__":
            self._focusindpen = wx.Pen(textclr, 1)
        else:
            self._focusindpen = wx.Pen(textclr, 1, wx.USER_DASH)
            self._focusindpen.SetDashes([1,1])
            self._focusindpen.SetCap(wx.CAP_BUTT)

    def SetDefault(self):
        self.GetParent().SetDefaultItem(self)

    def _GetLabelSize(self):
        w, h = self.GetTextExtent(self.GetLabel())
        return w, h, True

    def Notify(self):
        evt = SButtonEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.GetId())
        evt.SetIsDown(not self._isup)
        evt.SetButtonObj(self)
        evt.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(evt)

    def DrawMainButton(self, dc, width, height):
        w = min(width, height)

        if w <= 2:
            return

        # position = self.GetPosition()

        main, secondary = self.GetEllipseAxis()
        # xc = width / 2.0
        # yc = height / 2.0

        if abs(main - secondary) < 1e-6:
            # In This Case The Button Is A Circle
            if self._isup:
                img = self._mainbuttonup.Scale(w, w)
            else:
                img = self._mainbuttondown.Scale(w, w)
        else:
            # In This Case The Button Is An Ellipse... Some Math To Do
            # rect = self.GetRect()

            if main > secondary:
                # This Is An Ellipse With Main Axis Aligned With X Axis
                rect2 = w
                rect3 = w * secondary / main

            else:
                # This Is An Ellipse With Main Axis Aligned With Y Axis
                rect3 = w
                rect2 = w * main / secondary

            if self._isup:
                img = self._mainbuttonup.Scale(int(rect2), int(rect3))
            else:
                img = self._mainbuttondown.Scale(int(rect2), int(rect3))

        bmp = img.ConvertToBitmap()

        if abs(main - secondary) < 1e-6:
            if height > width:
                xpos = 0
                ypos = (height - width) / 2.0
            else:
                xpos = (width - height) / 2.0
                ypos = 0
        else:
            if height > width:
                if main > secondary:
                    xpos = 0
                    ypos = (height - rect3) / 2.0
                else:
                    xpos = (width - rect2) / 2.0
                    ypos = (height - rect3) / 2.0
            else:
                if main > secondary:
                    xpos = (width - rect2) / 2.0
                    ypos = (height - rect3) / 2.0
                else:
                    xpos = (width - rect2) / 2.0
                    ypos = 0

        gc = wx.GraphicsContext.Create(dc)
        # Draw Finally The Bitmap
        w, h = bmp.GetSize()
        gc.DrawBitmap(bmp, xpos, ypos, w, h)

        # Store Bitmap Position And Size To Draw An Elliptical Focus Indicator
        self._xpos = xpos
        self._ypos = ypos
        self._imgx = img.GetWidth()
        self._imgy = img.GetHeight()

    def DrawLabel(self, dc, width, height, dw=0, dh=0):
        dc.SetFont(self.GetFont())

        if self.IsEnabled():
            dc.SetTextForeground(self.GetLabelColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)

        w = min(width, height)

        # labeldelta Is Used To Give The Impression Of A "3D" Click
        if not self._isup:
            dw = dh = self._labeldelta

        angle = self.GetAngleOfRotation()*pi/180.0

        # Check If There Is Any Rotation Chosen By The User
        if angle == 0:
            dc.DrawText(label, (width-tw)//2+dw, (height-th)//2+dh)
        else:
            xc, yc = (width//2, height//2)

            xp = xc - (tw//2)* cos(angle) - (th//2)*sin(angle)
            yp = yc + (tw//2)*sin(angle) - (th//2)*cos(angle)

            dc.DrawRotatedText(label, int(xp + dw), int(yp + dh), angle*180/pi)

    def DrawFocusIndicator(self, dc, width, height):
        self._focusindpen.SetColour(self._focusclr)
        dc.SetLogicalFunction(wx.INVERT)
        dc.SetPen(self._focusindpen)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        main, secondary = self.GetEllipseAxis()

        if abs(main - secondary) < 1e-6:
            # Ah, That Is A Round Button
            if height > width:
                dc.DrawCircle(width//2, height//2, width//2-4)
            else:
                dc.DrawCircle(width//2, height//2, height//2-4)
        else:
            # This Is An Ellipse
            if hasattr(self, "_xpos"):
                dc.DrawEllipse(int(self._xpos + 2), int(self._ypos + 2), self._imgx - 4, self._imgy - 4)

        dc.SetLogicalFunction(wx.COPY)

    def OnSize(self, event):
        self.Refresh()
        event.Skip()

    def OnPaint(self, event):
        width, height = self.GetClientSize()

        # Use A Double Buffered DC (Good Speed Up)
        dc = wx.BufferedPaintDC(self)
        gcdc = wx.GCDC(dc)

        # The DC Background *Must* Be The Same As The Parent Background Colour,
        # In Order To Hide The Fact That Our "Shaped" Button Is Still Constructed
        # Over A Rectangular Window
        # brush = wx.Brush(self.GetParent().GetBackgroundColour())

        # gcdc.SetBackground(brush)
        gcdc.Clear()
        gcdc.Destroy()
        del gcdc

        self.DrawMainButton(dc, width, height)
        self.DrawLabel(dc, width, height)

        if self._hasfocus and self._usefocusind:
            self.DrawFocusIndicator(dc, width, height)

    def IsOutside(self, x, y):
        width, height = self.GetClientSize()
        diam = min(width, height)
        xc, yc = (width//2, height//2)

        main, secondary = self.GetEllipseAxis()

        if abs(main - secondary) < 1e-6:
            # This Is A Circle
            if ((x - xc)**2.0 + (y - yc)**2.0) > (diam/2.0)**2.0:
                return True
        else:
            # This Is An Ellipse
            mn = max(main, secondary)
            main = self._imgx/2.0
            secondary = self._imgy/2.0
            if (((x-xc)/main)**2.0 + ((y-yc)/secondary)**2.0) > 1:
                return True

        return False

    def OnLeftDown(self, event):
        if not self.IsEnabled():
            return

        x, y = (event.GetX(), event.GetY())

        if self.IsOutside(x,y):
            return

        self._isup = False

        if not self.HasCapture():
            self.CaptureMouse()

        self.SetFocus()

        self.Refresh()
        event.Skip()

    def OnLeftUp(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return

        if self.HasCapture():
            self.ReleaseMouse()

            if not self._isup:
                self.Notify()

            self._isup = True
            self.Refresh()
            event.Skip()

    def OnMotion(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return

        if event.LeftIsDown() and self.HasCapture():
            x, y = event.GetPosition()

            if self._isup and not self.IsOutside(x, y):
                self._isup = False
                self.Refresh()
                return

            if not self._isup and self.IsOutside(x,y):
                self._isup = True
                self.Refresh()
                return

        event.Skip()

    def OnGainFocus(self, event):
        self._hasfocus = True
        dc = wx.ClientDC(self)
        w, h = self.GetClientSize()

        if self._usefocusind:
            self.DrawFocusIndicator(dc, w, h)

    def OnLoseFocus(self, event):
        self._hasfocus = False
        dc = wx.ClientDC(self)
        w, h = self.GetClientSize()

        if self._usefocusind:
            self.DrawFocusIndicator(dc, w, h)

        self.Refresh()

    def OnKeyDown(self, event):
        if self._hasfocus and event.GetKeyCode() == ord(" "):

            self._isup = False
            self.Refresh()

        event.Skip()

    def OnKeyUp(self, event):
        if self._hasfocus and event.GetKeyCode() == ord(" "):

            self._isup = True
            self.Notify()
            self.Refresh()

        event.Skip()

    def MakePalette(self, tr, tg, tb):
        l = []
        for i in range(255):
            l.extend([tr*i // 255, tg*i // 255, tb*i // 255])

        return l

    def ConvertWXToPIL(self, bmp):
        width = bmp.GetWidth()
        height = bmp.GetHeight()
        img = Image.frombytes("RGBA", (width, height), bmp.GetData())

        return img

    def ConvertPILToWX(self, pil, alpha=True):
        if alpha:
            image = wx.Image(*pil.size)
            image.SetData(pil.convert("RGB").tobytes())
            image.SetAlpha(pil.convert("RGBA").tobytes()[3::4])
        else:
            image = wx.Image(pil.size[0], pil.size[1])
            new_image = pil.convert('RGB')
            data = new_image.tobytes()
            image.SetData(data)

        return image

    def SetAngleOfRotation(self, angle=None):
        if angle is None:
            angle = 0

        self._rotation = angle*pi/180

    def GetAngleOfRotation(self):
        return self._rotation*180.0/pi

    def SetEllipseAxis(self, main=None, secondary=None):
        if main is None:
            main = 1.0
            secondary = 1.0

        self._ellipseaxis = (main, secondary)

    def GetEllipseAxis(self):
        return self._ellipseaxis


class SBitmapButton(SButton):
    def __init__(self, parent, id, bitmap, pos=wx.DefaultPosition, size=wx.DefaultSize):
        self._bmpdisabled = None
        self._bmpfocus = None
        self._bmpselected = None

        self.SetBitmapLabel(bitmap)

        SButton.__init__(self, parent, id, "", pos, size)

    def GetBitmapLabel(self):
        return self._bmplabel

    def GetBitmapDisabled(self):
        return self._bmpdisabled

    def GetBitmapFocus(self):
        return self._bmpfocus

    def GetBitmapSelected(self):
        return self._bmpselected

    def SetBitmapDisabled(self, bitmap):
        self._bmpdisabled = bitmap

    def SetBitmapFocus(self, bitmap):
        self._bmpfocus = bitmap
        self.SetUseFocusIndicator(False)

    def SetBitmapSelected(self, bitmap):
        self._bmpselected = bitmap

    def SetBitmapLabel(self, bitmap, createothers=True):
        self._bmplabel = bitmap

        if bitmap is not None and createothers:
            dis_bitmap = wx.Bitmap(bitmap.ConvertToImage().ConvertToGreyscale())
            self.SetBitmapDisabled(dis_bitmap)

    def _GetLabelSize(self):
        if not self._bmplabel:
            return -1, -1, False

        return self._bmplabel.GetWidth() + 2, self._bmplabel.GetHeight() + 2, False

    def DrawLabel(self, dc, width, height, dw=0, dh=0):

        gc = wx.GraphicsContext.Create(dc)
        bmp = self._bmplabel

        if self._bmpdisabled and not self.IsEnabled():
            bmp = self._bmpdisabled

        if self._bmpfocus and self._hasfocus:
            bmp = self._bmpfocus

        if self._bmpselected and not self._isup:
            bmp = self._bmpselected

        bw, bh = bmp.GetWidth(), bmp.GetHeight()

        if not self._isup:
            dw = dh = self._labeldelta

        # hasMask = bmp.GetMask() is not None
        w, h = bmp.GetSize()
        gc.DrawBitmap(bmp, (width - bw) / 2.0 + dw, (height - bh) / 2.0 + dh, w, h)


class SBitmapTextButton(SBitmapButton):
    def __init__(self, parent, id, bitmap, label,
                 pos=wx.DefaultPosition, size=wx.DefaultSize):

        SBitmapButton.__init__(self, parent, id, bitmap, pos, size)
        self.SetLabel(label)

    def _GetLabelSize(self):
        w, h = self.GetTextExtent(self.GetLabel())

        if not self._bmplabel:
            return w, h, True       # if there isn't a bitmap use the size of the text

        w_bmp = self._bmplabel.GetWidth() + 2
        h_bmp = self._bmplabel.GetHeight() + 2
        width = w + w_bmp

        if h_bmp > h:
            height = h_bmp
        else:
            height = h

        return width, height, True

    def DrawLabel(self, dc, width, height, dw=0, dh=0):
        bmp = self._bmplabel

        if bmp is not None:     # if the bitmap is used

            if self._bmpdisabled and not self.IsEnabled():
                bmp = self._bmpdisabled

            if self._bmpfocus and self._hasfocus:
                bmp = self._bmpfocus

            if self._bmpselected and not self._isup:
                bmp = self._bmpselected

            bw, bh = bmp.GetWidth(), bmp.GetHeight()

            if not self._isup:
                dw = dh = self._labeldelta

            hasMask = bmp.GetMask() is not None

        else:

            bw = bh = 0     # no bitmap -> size is zero

        dc.SetFont(self.GetFont())

        if self.IsEnabled():
            dc.SetTextForeground(self.GetLabelColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)  # size of text

        if not self._isup:
            dw = dh = self._labeldelta

        w = min(width, height)

        pos_x = (width - bw - tw)//2 + dw      # adjust for bitmap and text to centre

        rotangle = self.GetAngleOfRotation()*pi/180.0

        if bmp is not None:
            if rotangle < 1.0/180.0:
                dc.DrawBitmap(bmp, pos_x, (height - bh)//2 + dh, hasMask) # draw bitmap if available
                pos_x = pos_x + 4   # extra spacing from bitmap
            else:
                pass

        if rotangle < 1.0/180.0:
            dc.DrawText(label, pos_x + dw + bw, (height-th)//2+dh)      # draw the text
        else:
            xc, yc = (width//2, height//2)
            xp = xc - (tw//2)* cos(rotangle) - (th//2)*sin(rotangle)
            yp = yc + (tw//2)*sin(rotangle) - (th//2)*cos(rotangle)
            dc.DrawRotatedText(label, xp, yp , rotangle*180.0/pi)


class __SToggleMixin(object):
    def SetToggle(self, flag):
        self._isup = not flag
        self.Refresh()

    SetValue = SetToggle

    def GetToggle(self):
        return not self._isup

    GetValue = GetToggle

    def OnLeftDown(self, event):
        if not self.IsEnabled():
            return

        x, y = (event.GetX(), event.GetY())

        if self.IsOutside(x,y):
            return

        self._saveup = self._isup
        self._isup = not self._isup

        if not self.HasCapture():
            self.CaptureMouse()

        self.SetFocus()
        self.Refresh()

    def OnLeftUp(self, event):
        if not self.IsEnabled() or not self.HasCapture():
            return

        if self.HasCapture():
            if self._isup != self._saveup:
                self.Notify()

            self.ReleaseMouse()
            self.Refresh()

    def OnKeyDown(self, event):
        event.Skip()

    def OnMotion(self, event):
        if not self.IsEnabled():
            return

        if event.LeftIsDown() and self.HasCapture():

            x, y = event.GetPosition()
            w, h = self.GetClientSize()

            if not self.IsOutside(x, y):
                self._isup = not self._saveup
                self.Refresh()
                return

            if self.IsOutside(x,y):
                self._isup = self._saveup
                self.Refresh()
                return

        event.Skip()

    def OnKeyUp(self, event):
        if self._hasfocus and event.GetKeyCode() == ord(" "):

            self._isup = not self._isup
            self.Notify()
            self.Refresh()

        event.Skip()


class SToggleButton(__SToggleMixin, SButton):
    pass


class SBitmapToggleButton(__SToggleMixin, SBitmapButton):
    pass


class SBitmapTextToggleButton(__SToggleMixin, SBitmapTextButton):
    pass


if __name__ == '__main__':

    import wx

    class MyFrame(wx.Frame):

        def __init__(self, parent):

            wx.Frame.__init__(self, parent, -1, "ShapedButton Demo")

            panel = wx.Panel(self)

            # Create bitmaps for the button
            bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER, (16, 16))

            play = SBitmapToggleButton(panel, -1, bmp, (100, 50))
            play.SetUseFocusIndicator(False)


    # our normal wxApp-derived class, as usual

    app = wx.App(0)

    frame = MyFrame(None)
    app.SetTopWindow(frame)
    frame.Show()

    app.MainLoop()
