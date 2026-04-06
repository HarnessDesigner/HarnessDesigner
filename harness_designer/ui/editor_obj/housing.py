from typing import TYPE_CHECKING

import wx
from wx import propgrid as wxpg

from .prop_grid import long_string_prop as _long_string_prop


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from ... import ui as _ui


class Housing(wxpg.PropertyGrid):

    def __init__(self, parent, mainframe: "_ui.MainFrame", db_obj: "_pjt_housing"):
        wxpg.PropertyGrid.__init__(self, parent, wx.ID_ANY)

        self.db_obj = db_obj
        self.part = db_obj.part

        part_cat = wxpg.PropertyCategory('Part Attributes')

        part_cat.AppendChild(wxpg.StringProperty('Part Number', 'part_number', self.part.part_number))
        part_cat.AppendChild(_long_string_prop.LongStringProperty('Description', 'description', self.part.description))

        '''
        'Part Attributes'

            'Part Number', part_number
            'Description', description
            'Manufacturer', mfg_id
            'Family', family_id
            'Series', series_id
            'Color', color_id

            'Documentation'
                'Image', image_id
                'Datasheet', datasheet_id
                'CAD', cad_id
                '3D Model', model3d_id

            'Environmental Attributes'
                'Min Temperature', min_temp_id
                'Max Temperature', max_temp_id
                'IP Rating', ip_rating_id

            `Additional Information'
                'Cavity Lock Type', cavity_lock_id
                'Seal Type', seal_type_id
                'CPA Lock Type', cpa_lock_type_id
                'Is Sealable', sealing


            'Pin Information'
                'Rows', rows
                'Pin Count', num_pins
                'Terminal Sizes', terminal_sizes
                'Size Counts', terminal_size_counts
                'Pitch' centerline

            'Physical Attributes'
                'Gender', gender_id
                'Direction', direction_id
                'Length', length
                'Width', width
                'Height', height
                'Weight', weight
                'Angle 3D', angle3d


            'Accessory Arrachment Positions'
                'Cover Position', cover_position3d
                'Seal Position', seal_position3d
                'Boot Position', boot_position3d
                'TPA Lock Position', tpa_lock_1_position3d
                'TPA Lock Position', tpa_lock_2_position3d
                'CPA Lock Position', cpa_lock_position3d

            'Compatable Parts'
                'CPAs', compat_cpas_array
                'TPAs', compat_tpas_array
                'Covers', compat_covers_array
                'Terminals', compat_terminals_array
                'Seals', compat_seals_array
                'Housings', compat_housings_array
                'Boots', compat_boots_array


        'Project Attributes'
            'Name', name
            'Notes', notes

            '3D'
                'Position', position3d
                'Angle', angle3d
                'Visible', is_visible3d

            '2D'
                'Position', position2d
                'Angle', angle2d
                'Visible', is_visible2d





        :param db_obj:
        '''

