'''
cad
image
datasheet
model3d
'''


from ..database.global_db import cover as _cover
from ..database import global_db as _global_db

from .controls import generic_textctrl as _generic_textctrl
from .controls import part_numberctrl as _part_numberctrl
from .controls import manufacturerctrl as _manufacturerctrl
from .controls import descriptionctrl as _descriptionctrl
from .controls import familyctrl as _familyctrl
from .controls import seriesctrl as _seriesctrl
from .controls import tempctrl as _tempctrl
from .controls import colorctrl as _colorctrl
from .controls import directionctrl as _directionctrl
from .controls import weightctrl as _weightctrl
from .controls import dimensionctrl as _dimensionctrl

from . import AttributePanel as _AttributePanel


class CoverAttrPanel(_AttributePanel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        _AttributePanel.__init__(self, parent, global_db, (0, 200, 0, 255),
                                 (100, 100, 100, 255), (0, 0, 0, 255))

        general_panel = self.AppendBar('General')
        self.pn_ctrl = _part_numberctrl.PartNumberCtrl(general_panel)
        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(general_panel)
        self.color_ctrl = _colorctrl.ColorCtrl(general_panel, global_db, 'Color:')
        self.weight_ctrl = _weightctrl.WeightCtrl(general_panel)
        self.pins_ctrl = _generic_textctrl.GenericTextCtrl(general_panel, 'Pins:')
        self.direction_ctrl = _directionctrl.DirectionCtrl(general_panel, global_db)

        mfg_panel = self.AppendBar('Manufacturer')
        self.mfg_ctrl = _manufacturerctrl.ManufacturerCtrl(mfg_panel, global_db)

        family_panel = self.AppendBar('Family')
        self.family_ctrl = _familyctrl.FamilyCtrl(family_panel, global_db)

        series_panel = self.AppendBar('Series')
        self.series_ctrl = _seriesctrl.SeriesCtrl(series_panel, global_db)

        dimensions_panel = self.AppendBar('Dimensions')
        self.dimension_ctrl = _dimensionctrl.DimensionCtrl(dimensions_panel)

        temp_panel = self.AppendBar('Temperatures')
        self.mintemp_ctrl = _tempctrl.TempCtrl(temp_panel, global_db, 'Min Temp:')
        self.maxtemp_ctrl = _tempctrl.TempCtrl(temp_panel, global_db, 'Max Temp:')

    def on_save(self, evt):
        if self.db_obj is not None:
            part_number = self.pn_ctrl.GetValue()
            description = self.desc_ctrl.GetValue()
            color_id = self.color_ctrl.GetValue()
            weight = self.weight_ctrl.GetValue()
            mfg_id = self.mfg_ctrl.GetValue()
            series_id = self.series_ctrl.GetValue()
            family_id = self.family_ctrl
            min_temp_id = self.mintemp_ctrl.GetValue()
            max_temp_id = self.maxtemp_ctrl.GetValue()
            direction_id = self.direction_ctrl.GetValue()
            pins = self.pins_ctrl.GetValue()
            length, width, height = self.dimension_ctrl.GetValue()

            self.global_db.covers_table.update(
                self.db_obj.db_id,
                part_number=part_number, mfg_id=mfg_id, description=description,
                series_id=series_id, image_id=image_id, datasheet_id=datasheet_id,
                cad_id=cad_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                color_id=color_id, weight=weight, family_id=family_id, length=length,
                width=width, height=height, pins=pins, direction_id=direction_id)

        evt.Skip()

    def SetDBObject(self, db_obj: _cover.Cover):
        self.db_obj = db_obj

        self.pn_ctrl.SetValue(db_obj.part_number)
        self.desc_ctrl.SetValue(db_obj.description)
        self.color_ctrl.SetDBObject(db_obj.color)
        self.weight_ctrl.SetValue(db_obj.weight)

        self.mfg_ctrl.SetDBObject(db_obj.manufacturer)
        self.series_ctrl.SetDBObject(db_obj.series)
        self.family_ctrl.SetDBObject(db_obj.family)
        self.mintemp_ctrl.SetDBObject(db_obj.min_temp)
        self.maxtemp_ctrl.SetDBObject(db_obj.max_temp)

        self.dimension_ctrl.SetValue(db_obj.length, db_obj.width, db_obj.height)

        self.direction_ctrl.SetDBObject(db_obj.direction)
