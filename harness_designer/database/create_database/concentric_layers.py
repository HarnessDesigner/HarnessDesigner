
from . import projects as _projects
from . import concentrics as _concentrics

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_concentric_layers',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('concentric_id', no_null=True,
                  references=_con.SQLFieldReference(_concentrics.pjt_table,
                                                    _concentrics.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.FloatField('diameter', default='"0.0"', no_null=True),
    _con.IntField('num_wires', default='0', no_null=True),
    _con.IntField('num_fillers', default='0', no_null=True),
    _con.TextField('notes', default='""', no_null=True)
)
