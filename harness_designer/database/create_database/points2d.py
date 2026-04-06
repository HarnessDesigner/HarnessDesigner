
from . import projects as _projects

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_points2d',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True)
)
