from wx import propgrid as wxpg

from . import combobox_prop as _combobox_prop
from . import angle_prop as _angle_prop
from . import choice_prop as _choice_prop
from . import float_prop as _float_prop
from . import position_prop as _position_prop


wxpg.PropertyGrid.RegisterEditorClass(_float_prop.FloatSpinEditor())
wxpg.PropertyGrid.RegisterEditorClass(_combobox_prop.ComboboxEditor())
wxpg.PropertyGrid.RegisterEditorClass(_combobox_prop.ComboboxEditor())
wxpg.PropertyGrid.RegisterEditorClass(_float_prop.FloatSpinEditor())
wxpg.PropertyGrid.RegisterEditorClass(_combobox_prop.ComboboxEditor())
