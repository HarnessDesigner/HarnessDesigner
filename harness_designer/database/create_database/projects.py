# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from . import models3d as _models3d
from . import colors as _colors

pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'projects',
    pjt_id_field,
    _con.IntField('model_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('color_id', default='0',
                  references=_con.SQLFieldReference(_colors.table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('creator', default='""', no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('object_count', default='0', no_null=True),
    # Length (mm) actually *required* to cover every wire's stripe_clip_stop
    # in this project -- NOT the size the shared helix VBO (shapes/helix.py)
    # gets built at. objects3d.wire.WireStripe._ensure_stripe_capacity pads this
    # by _HELIX_OVERSHOOT_MM whenever it actually rebuilds the VBO, so a
    # live drag/preview has headroom to grow without triggering a GPU
    # reallocation on every frame. See Project.wire_stripe_max_length.
    _con.FloatField('wire_stripe_max_length', default='1000.0', no_null=True)
)
