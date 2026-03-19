

from ... import config as _config

CONNECTOR_SQLITE = 0
CONNECTOR_MYSQL = 1

Config = _config.Config


if Config.database.connector == CONNECTOR_SQLITE:
    from .sqlite_connector import SQLConnector
    from .sqlite_connector import sql_table

    REFERENCE_DEFAULT = sql_table.REFERENCE_DEFAULT
    REFERENCE_CASCADE = sql_table.REFERENCE_CASCADE
    SQLTable = sql_table.SQLTable
    SQLFieldReference = sql_table.SQLFieldReference
    PrimaryKeyField = sql_table.PrimaryKeyField
    BytesField = sql_table.BytesField
    FloatField = sql_table.FloatField
    IntField = sql_table.IntField
    TextField = sql_table.TextField
    BlobField = sql_table.BlobField

elif Config.database.connector == CONNECTOR_MYSQL:
    from .mysql_connector import SQLConnector
else:
    raise RuntimeError('Unknown connector type')
