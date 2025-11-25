
from ..database.global_db import bundle_cover as _bundle_cover
from ..database import global_db as _global_db

from .controls import generic_floatctrl as _generic_floatctrl
from .controls import generic_textctrl as _generic_textctrl
from .controls import part_numberctrl as _part_numberctrl
from .controls import manufacturerctrl as _manufacturerctrl
from .controls import descriptionctrl as _descriptionctrl
from .controls import seriesctrl as _seriesctrl
from .controls import tempctrl as _tempctrl
from .controls import colorctrl as _colorctrl
from .controls import materialctrl as _materialctrl
from .controls import adhesivectrl as _adhesivectrl
from .controls import weightctrl as _weightctrl

from . import AttributePanel as _AttributePanel


class BundleAttribPanel(_AttributePanel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        _AttributePanel.__init__(self, parent, global_db, (0, 200, 0, 255),
                                 (100, 100, 100, 255), (0, 0, 0, 255))

        general_panel = self.AppendBar('General')
        self.pn_ctrl = _part_numberctrl.PartNumberCtrl(general_panel)
        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(general_panel)
        self.color_ctrl = _colorctrl.ColorCtrl(general_panel, global_db, 'Color:')
        self.weight_ctrl = _weightctrl.WeightCtrl(general_panel)
        self.min_size_ctrl = _generic_floatctrl.GenericFloatCtrl(general_panel, 'Min Size:', 'mm')
        self.max_size_ctrl = _generic_floatctrl.GenericFloatCtrl(general_panel, 'Max Size:', 'mm')

        mfg_panel = self.AppendBar('Manufacturer')
        self.mfg_ctrl = _manufacturerctrl.ManufacturerCtrl(mfg_panel, global_db)

        series_panel = self.AppendBar('Series')
        self.series_ctrl = _seriesctrl.SeriesCtrl(series_panel, global_db)

        props_panel = self.AppendBar('Properties')
        self.material_ctrl = _materialctrl.MaterialCtrl(props_panel, global_db)
        self.adhesive_ctrl = _adhesivectrl.AdhesiveCtrl(props_panel, global_db)
        self.shrink_ratio_ctrl = _generic_textctrl.GenericTextCtrl(props_panel, 'Shrink Ratio:')
        self.rigidity_ctrl = _generic_textctrl.GenericTextCtrl(props_panel, 'Rigidity:')
        self.wall_ctrl = _generic_textctrl.GenericTextCtrl(props_panel, 'Wall Type:')
        self.protection_ctrl = _generic_textctrl.GenericTextCtrl(props_panel, 'Protection:')

        temp_panel = self.AppendBar('Temperatures')
        self.mintemp_ctrl = _tempctrl.TempCtrl(temp_panel, global_db, 'Min Temp:')
        self.maxtemp_ctrl = _tempctrl.TempCtrl(temp_panel, global_db, 'Max Temp:')
        self.shrinktemp_ctrl = _tempctrl.TempCtrl(temp_panel, global_db, 'Shrink Temp:')

    def on_save(self, evt):
        if self.db_obj is not None:
            part_number = self.pn_ctrl.GetValue()
            description = self.desc_ctrl.GetValue()
            color_id = self.color_ctrl.GetValue()
            weight = self.weight_ctrl.GetValue()
            mfg_id = self.mfg_ctrl.GetValue()
            series_id = self.series_ctrl.GetValue()
            min_temp_id = self.mintemp_ctrl.GetValue()
            max_temp_id = self.maxtemp_ctrl.GetValue()
            min_size = self.min_size_ctrl.GetValue()
            max_size = self.max_size_ctrl.GetValue()
            material_id = self.material_ctrl.GetValue()
            adhesives = self.adhesive_ctrl.GetValue()
            shrink_ratio = self.shrink_ratio_ctrl.GetValue()
            rigidity = self.rigidity_ctrl.GetValue()
            wall = self.wall_ctrl.GetValue()
            protections = self.protection_ctrl.GetValue()
            shrink_temp_id = self.shrinktemp_ctrl.GetValue()

            self.global_db.bundle_covers_table.update(
                self.db_obj.db_id,
                part_number=part_number, mfg_id=mfg_id, description=description,
                series_id=series_id, image_id=image_id, datasheet_id=datasheet_id,
                cad_id=cad_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                color_id=color_id, min_size=min_size, max_size=max_size, wall=wall,
                shrink_ratio=shrink_ratio, protections=protections, material_id=material_id,
                rigidity=rigidity, shrink_temp_id=shrink_temp_id, adhesives=adhesives,
                weight=weight)

        evt.Skip()

    def SetDBObject(self, db_obj: _bundle_cover.BundleCover):
        self.db_obj = db_obj

        self.pn_ctrl.SetValue(db_obj.part_number)
        self.desc_ctrl.SetValue(db_obj.description)
        self.color_ctrl.SetDBObject(db_obj.color)
        self.weight_ctrl.SetValue(db_obj.weight)

        self.mfg_ctrl.SetDBObject(db_obj.manufacturer)
        self.series_ctrl.SetDBObject(db_obj.series)
        self.mintemp_ctrl.SetDBObject(db_obj.min_temp)
        self.maxtemp_ctrl.SetDBObject(db_obj.max_temp)

        self.min_size_ctrl.SetValue(db_obj.min_size)
        self.max_size_ctrl.SetValue(db_obj.max_size)
        self.material_ctrl.SetDBObject(db_obj.material)
        self.adhesive_ctrl.SetDBObject(db_obj.adhesives)
        self.shrink_ratio_ctrl.SetValue(db_obj.shrink_ratio)
        self.rigidity_ctrl.SetValue(db_obj.rigidity)
        self.wall_ctrl.SetValue(db_obj.wall)
        self.protection_ctrl.SetValue(db_obj.protections)
        self.shrinktemp_ctrl.SetDBObject(db_obj.shrink_temp)
