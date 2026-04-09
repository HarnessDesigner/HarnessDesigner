import wx

from prop_grid import props as _props
import prop_grid as _prop_grid


class Frame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, size=(400, 600))

        prop_grid = _prop_grid.PropertyGrid(self)

        cat = _prop_grid.Category('Test1')

        prop1 = _props.FloatProperty('Prop1', 'prop1', value=25.0, min_value=10.0, max_value=50.0, increment=0.1, units='mm')
        prop2 = _props.IntProperty('Test Prop2', 'prop2', value=25, min_value=10, max_value=50, units='cm')
        prop3 = _props.StringProperty('Another Prop3', 'prop3', 'This is a simple test string')
        prop4 = _props.LongStringProperty('Another Test Prop4', 'prop4', 'This is a\nmulti line test string')
        prop5 = _props.ArrayIntProperty('Prop5', 'prop5', [1, 2, 3, 4, 5])
        prop6 = _props.ArrayFloatProperty('Blah Prop6', 'prop6', [1.0, 2.0, 3.0, 4.0, 5.0])
        prop7 = _props.ArrayStringProperty('Blah Blah Prop7', 'prop7', ['one', 'two', 'three', 'four', 'five'])
        prop8 = _props.BoolProperty('Prop8', 'prop8', False)
        prop9 = _props.ComboBoxProperty('Prop9', 'prop9', 'one', ['one', 'two', 'three', 'four', 'five'])
        cat.Append(prop1)
        cat.Append(prop2)
        cat.Append(prop3)
        cat.Append(prop4)
        cat.Append(prop5)
        cat.Append(prop6)
        cat.Append(prop7)
        cat.Append(prop8)
        cat.Append(prop9)

        prop_grid.Append(cat)

        # _props.BitmapComboBoxProperty
        # _props.ColorProperty
        # _props.DatasheetCADProperty
        # _props.ImageProperty

        prop1 = _props.FloatProperty('Prop1', 'prop1', value=25.0, min_value=10.0, max_value=50.0, increment=0.1, units='mm')
        prop2 = _props.IntProperty('Test Prop2', 'prop2', value=25, min_value=10, max_value=50, units='cm')
        prop3 = _props.StringProperty('Another Prop3', 'prop3', 'This is a simple test string')

        cat = _prop_grid.Category('Test2')
        x = _props.FloatProperty('x', 'x', value=25.0, min_value=10.0, max_value=50.0, increment=0.01, units='mm')
        y = _props.FloatProperty('y', 'y', value=25.0, min_value=10.0, max_value=50.0, increment=0.01, units='mm')
        z = _props.FloatProperty('z', 'z', value=25.0, min_value=10.0, max_value=50.0, increment=0.01, units='mm')

        position1 = _props.Property('Position1', 'position1')
        position1.AppendChild(x)
        position1.AppendChild(y)
        position1.AppendChild(z)

        x = _props.IntProperty('x', 'x', value=25, min_value=10, max_value=50, units='cm')
        y = _props.IntProperty('y', 'y', value=25, min_value=10, max_value=50, units='cm')
        z = _props.IntProperty('z', 'z', value=25, min_value=10, max_value=50, units='cm')
        position2 = _props.Property('Position2', 'position2')
        position2.AppendChild(x)
        position2.AppendChild(y)
        position2.AppendChild(z)

        group = _props.Property('Test Group')

        prop4 = _props.LongStringProperty('Prop4', 'prop4', 'This is a\nmulti line test string')
        prop5 = _props.ArrayIntProperty('Prop5', 'prop5', [1, 2, 3, 4, 5])
        prop6 = _props.ArrayFloatProperty('Prop6', 'prop6', [1.0, 2.0, 3.0, 4.0, 5.0])
        prop7 = _props.ArrayStringProperty('Prop7', 'prop7', ['one', 'two', 'three', 'four', 'five'])
        prop8 = _props.BoolProperty('Prop8', 'prop8', False)
        prop9 = _props.ComboBoxProperty('Prop9', 'prop9', 'one', ['one', 'two', 'three', 'four', 'five'])

        group.AppendChild(prop4)
        group.AppendChild(prop5)
        group.AppendChild(prop6)
        group.AppendChild(prop7)
        group.AppendChild(prop8)
        group.AppendChild(prop9)

        cat.Append(position1)
        cat.Append(prop1)
        cat.Append(prop2)
        cat.Append(group)
        cat.Append(prop3)
        cat.Append(position2)

        prop_grid.Append(cat)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(prop_grid, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)
        self.Layout()


app = wx.App()


frame = Frame()
frame.Show()

app.MainLoop()
