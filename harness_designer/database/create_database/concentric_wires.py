
from . import projects as _projects
from . import concentric_layers as _concentric_layers
from . import wires as _wires
from . import points2d as _points2d

from .. import db_connectors as _con
from ... import logger as _logger


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_concentric_wires',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('layer_id', no_null=True,
                  references=_con.SQLFieldReference(_concentric_layers.pjt_table,
                                                    _concentric_layers.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('wire_id', no_null=True,
                  references=_con.SQLFieldReference(_wires.pjt_table,
                                                    _wires.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.IntField('is_filler', no_null=True),
    _con.TextField('notes', default='""', no_null=True)
)
