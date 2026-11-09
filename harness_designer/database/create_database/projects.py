# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from . import models3d as _models3d
from . import colors as _colors

pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'projects',
    pjt_id_field,
    _con.UUIDField('model_id', default='NULL',
                   references=_con.SQLFieldReference(_models3d.table,
                                                     _models3d.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('color_id', default="X'00000000000000000000000000000000'",
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('creator', default='""', no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('object_count', default='0', no_null=True),
    # Length (mm) the shared helix VBO (shapes/helix.py) was last needed at. The 3D and board wires no longer use that mesh (a
    # wire's stripe is a material drawn by the tube shader), so nothing writes this any more; it is kept with
    # Project.wire_stripe_max_length until the column is dropped.
    _con.FloatField('wire_stripe_max_length', default='1000.0', no_null=True),
    # The extent of everything the project occupies in each editor view, as
    # a list string ``[[min_x, min_y, min_z], [max_x, max_y, max_z]]`` --
    # read once when the project loads (to frame the camera before any
    # object exists) and written once when it unloads/the app closes, from
    # that view's AABB pool. NULL until the project has been unloaded once.
    # See Project.bounds_3d/bounds_schematic/bounds_pegboard.
    _con.TextField('bounds_3d', default='NULL'),
    _con.TextField('bounds_schematic', default='NULL'),
    _con.TextField('bounds_pegboard', default='NULL')
)
