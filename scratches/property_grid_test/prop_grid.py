import wx
from wx import propgrid as wxpg


def _d(val):
    return val


def remap(value: int | float,
          old_min: int | float, old_max: int | float,
          new_min: int | float, new_max: int | float,
          type=float) -> int | float:  # NOQA
    """
    Remaps/Reranges a value from one range to another range.

    Lets say you have a value of 25 and that value fits into a range of 1-100.
    You need that value to fit into the 1-250 range but still be 25% of the range
    like it is in the 0-100 range. This is the function to use to do that.

    :param value: input value

    :param old_min: input value's minimum

    :param old_max: input values maximum
    :param new_min: new minimum
    :param new_max: new maximum
    :param type: what type to return the value as; `int`, `float` or `Decimal`
    :return: The new value mapped to the new range
    """
    value = _d(value)
    old_min = _d(old_min)
    old_max = _d(old_max)
    new_min = _d(new_min)
    new_max = _d(new_max)

    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min

    return type(new_value)





class TrivialPropertyEditor(wxpg.PGEditor):
    """
    This is a simple re-creation of TextCtrlWithButton. Note that it does
    not take advantage of wx.TextCtrl and wx.Button creation helper functions
    in wx.PropertyGrid.
    """
    def __init__(self):
        wxpg.PGEditor.__init__(self)

    def CreateControls(self, propgrid, prop, pos, sz):
        """ Create the actual wxPython controls here for editing the
            property value.

            You must use propgrid.GetPanel() as parent for created controls.

            Return value is either single editor control or tuple of two
            editor controls, of which first is the primary one and second
            is usually a button.
        """
        try:
            x, y = pos
            w, h = sz
            h = 64 + 6

            # Make room for button
            bw = propgrid.GetRowHeight()
            w -= bw

            s = prop.GetDisplayedString()

            tc = wx.TextCtrl(propgrid.GetPanel(), wx.ID_ANY, s, (x, y), (w, h), wx.TE_PROCESS_ENTER)
            btn = wx.Button(propgrid.GetPanel(), wx.ID_ANY, '...', (x + w, y), (bw, h), wx.WANTS_CHARS)
            return wxpg.PGWindowList(tc, btn)
        except:
            import traceback
            print(traceback.print_exc())

    def UpdateControl(self, prop, ctrl):
        ctrl.SetValue(prop.GetDisplayedString())

    # def DrawValue(self, dc, rect, prop, text):
    #     if not prop.IsValueUnspecified():
    #         dc.DrawText(prop.GetDisplayedString(), rect.x+5, rect.y)

    def OnEvent(self, propgrid, prop, ctrl, event):
        """ Return True if modified editor value should be committed to
            the property. To just mark the property value modified, call
            propgrid.EditorsValueWasModified().
        """
        if not ctrl:
            return False

        evtType = event.GetEventType()

        if evtType == wx.wxEVT_COMMAND_TEXT_ENTER:
            if propgrid.IsEditorsValueModified():
                return True
        elif evtType == wx.wxEVT_COMMAND_TEXT_UPDATED:
            #
            # Pass this event outside wxPropertyGrid so that,
            # if necessary, program can tell when user is editing
            # a textctrl.
            event.Skip()
            event.SetId(propgrid.GetId())

            propgrid.EditorsValueWasModified()
            return False

        return False

    def GetValueFromControl(self, prop, ctrl):
        """ Return tuple (wasSuccess, newValue), where wasSuccess is True if
            different value was acquired successfully.
        """
        tc = ctrl
        textVal = tc.GetValue()

        if prop.UsesAutoUnspecified() and not textVal:
            return True, None

        res, value = prop.StringToValue(textVal, wxpg.PG_FULL_VALUE)

        # Changing unspecified always causes event (returning
        # True here should be enough to trigger it).
        if not res and value is None:
            res = True

        return res, value

    def SetValueToUnspecified(self, prop, ctrl):
        ctrl.Remove(0, len(ctrl.GetValue()))

    def SetControlStringValue(self, prop, ctrl, text):
        ctrl.SetValue(text)

    def OnFocus(self, prop, ctrl):
        ctrl.SetSelection(-1, -1)


import os







class Point:

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class PropertyGrid(wxpg.PropertyGrid):

    def __init__(self, parent):
        wxpg.PropertyGrid.__init__(self, parent, wx.ID_ANY)

        point = Point(10.0, 62.8, 97.1)

        prop = Point3DProperty('Test', 'test', point)

        self.Append(prop)


        # propgrid.ArrayStringProperty
        # propgrid.ColourProperty
        # propgrid.DateProperty
        # propgrid.DirProperty
        # propgrid.EditEnumProperty
        # propgrid.EditorDialogProperty
        # propgrid.EnumProperty
        # propgrid.FileProperty
        # propgrid.FlagsProperty
        # propgrid.FloatProperty
        # propgrid.ImageFileProperty
        # propgrid.IntProperty
        # propgrid.LongStringProperty
        # propgrid.MultiChoiceProperty
        # propgrid.StringProperty
        # propgrid.UIntProperty
        #
        #
        # PropertyCategory
        #
        # PropertyGridManager
        # PropertyGridPage
        #
        # propgrid.PyChoiceEditor
        # propgrid.PyComboBoxEditor
        # propgrid.PyArrayStringProperty
        # propgrid.PyColourProperty
        # propgrid.PyEditEnumProperty
        # propgrid.PyEditor
        # propgrid.PyEditorDialogAdapter
        # propgrid.PyEnumProperty
        # propgrid.PyFileProperty
        # propgrid.PyFlagsProperty
        # propgrid.PyFloatProperty
        # propgrid.PyIntProperty
        # propgrid.PyLongStringProperty
        # propgrid.PyProperty
        # propgrid.PyStringProperty
        # propgrid.PyUIntProperty


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, size=(400, 600))

        prop_grid = PropertyGrid(self)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(prop_grid, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)



app = wx.App()

wxpg.PropertyGrid.RegisterEditorClass(FloatSpinEditor())


frame = Frame()
frame.Show()

app.MainLoop()




