from ... import db_connectors as _con

'''


id_field = _con.PrimaryKeyField('id')

wires_table = _con.SQLTable(
    'wires',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.manufacturers_table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('family_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_families.families_table,
                                                    _families.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('series_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_series.series_table,
                                                    _series.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('color_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_colors.colors_table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.materials_table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.resources_table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datacheet_idmfg_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.resources_table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.resources_table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.temperatures_table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.temperatures_table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stripe_color_id', default='999999', no_null=True,
                  references=_con.SQLFieldReference(_colors.colors_table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('num_conductors', default='1', no_null=True),
    _con.IntField('shielded', default='0', no_null=True),
    _con.FloatField('tpi', default='"0.0"', no_null=True),
    _con.FloatField('conductor_dia_mm', default='NULL'),
    _con.FloatField('size_mm2', default='NULL'),
    _con.IntField('size_awg', default='NULL'),
    _con.FloatField('od_mm', no_null=True),
    _con.FloatField('weight_1km', default='"0.0"', no_null=True),
    _con.IntField('core_material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.platings_table,
                                                    _platings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('resistance_ikm', default='"0.0"', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True)
)


'''

def cavities(con, cur):
    # cavities point positions are relitive to the housing with the
    # housing being centered at x=0, y=0, z=0

    cur.execute('CREATE TABLE cavities('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'housing_id INTEGER NOT NULL, '
                'idx INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'point2d TEXT DEFAULT "[0.0, 0.0]" NOT NULL, '                
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'length REAL DEFAULT "2.0" NOT NULL, '
                'terminal_sizes TEXT DEFAULT "[]" NOT NULL, '
                'FOREIGN KEY (housing_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
                ');')
    con.commit()
