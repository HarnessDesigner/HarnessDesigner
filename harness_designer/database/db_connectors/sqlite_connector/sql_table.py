# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""SQLite-flavored SQL table and field definition helpers."""

from ....import logger as _logger
from .... import check_types as _check_types

FIELD_TYPE_REAL = 'REAL'
FIELD_TYPE_TEXT = 'TEXT'
FIELD_TYPE_INT = 'INTEGER'
FIELD_TYPE_BLOB = 'BLOB'
FIELD_TYPE_UUID = 'BLOB'

REFERENCE_CASCADE = 'CASCADE'
REFERENCE_DEFAULT = 'SET DEFAULT'


class SQLTable:

    """Describe a SQL table definition for the SQLite connector.
    """
    @_check_types.do
    def __init__(self, name: str, *fields: "SQLField"):
        """Initialize the table definition.

        :param name: Table name to represent.
        :type name: str
        :param *fields: Field definitions that belong to the table.
        :type *fields: 'SQLField'
        """
        self.name = name
        self.fields = fields

    @_check_types.do
    def is_in_db(self, db_cursor) -> bool:
        """Return whether the table already exists in the database.

        :param db_cursor: Database cursor or connector wrapper used to execute SQL.
        :type db_cursor: UNKNOWN

        :returns: ``True`` when the table exists; otherwise ``False``.
        :rtype: bool
        """
        db_cursor._con.execute(f'SELECT name FROM {db_cursor.database_name}.sqlite_master WHERE type="table";')
        rows = db_cursor._con.fetchall()

        table_names = [row[0] for row in rows]

        return self.name in table_names

    @_check_types.do
    def is_ok(self, db_cursor) -> bool:
        """Return whether the existing table still needs field updates.

        :param db_cursor: Database cursor or connector wrapper used to execute SQL.
        :type db_cursor: UNKNOWN

        :returns: ``True`` when the table requires updates; otherwise ``False``.
        :rtype: bool
        """
        # pragma_table_xinfo, not pragma_table_info -- the latter silently
        # omits GENERATED columns (e.g. ProjectIdField's project_id) on this
        # SQLite build, which made every pjt_*/project_id table look like it
        # always needed an update, even immediately after being created with
        # that column already in place (ALTER TABLE ADD COLUMN then fails
        # with "duplicate column name").
        db_cursor._con.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                               f'pragma_table_xinfo("{self.name}");')

        column_names = eval(db_cursor._con.fetchall()[0][0])

        for field in self.fields:
            if field.name not in column_names:
                return True

        return False

    @_check_types.do
    def update_fields(self, db_cursor):

        """Add any missing fields to an existing table.

        :param db_cursor: Database cursor or connector wrapper used to execute SQL.
        :type db_cursor: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        # See is_ok() -- pragma_table_xinfo, not pragma_table_info, so
        # GENERATED columns already present aren't re-added here.
        db_cursor._con.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                               f'pragma_table_xinfo("{self.name}");')

        column_names = eval(db_cursor._con.fetchall()[0][0])

        for field in self.fields:
            if field.name not in column_names:
                field.add_to_table(db_cursor, self.name)

    @_check_types.do
    def add_to_db(self, db_cursor):
        """Create the table in the database.

        :param db_cursor: Database cursor or connector wrapper used to execute SQL.
        :type db_cursor: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        fields = [str(field) for field in self.fields]

        for i, field in enumerate(fields[:]):
            if 'FOREIGN KEY' in field:
                field, foreign_key = field.rsplit(',', 1)
                fields[i] = field
                fields.append(foreign_key)

        fields = ', '.join(fields)

        _logger.database(f'CREATE TABLE {self.name} ({fields});')

        db_cursor._con.execute(f'CREATE TABLE {self.name} ({fields});')
        db_cursor._con.commit()


class SQLFieldReference:

    """Represent a foreign-key reference for a SQL field.
    """
    @_check_types.do
    def __init__(self, table: SQLTable, field: "SQLField", on_delete=REFERENCE_DEFAULT, on_update=REFERENCE_DEFAULT):
        """Initialize the foreign-key reference metadata.

        :param table: Referenced parent table.
        :type table: SQLTable
        :param field: Referenced field in the parent table.
        :type field: 'SQLField'
        :param on_delete: Action applied when the referenced row is deleted.
        :type on_delete: UNKNOWN
        :param on_update: Action applied when the referenced row is updated.
        :type on_update: UNKNOWN
        """
        self.table = table
        self.field = field
        self.on_delete = on_delete
        self.on_update = on_update

    @_check_types.do
    def __str__(self):
        return (f' REFERENCES {self.table.name}({self.field.name}) '
                f'ON DELETE {self.on_delete} '
                f'ON UPDATE {self.on_update}')

    @_check_types.do
    def format(self, field_name):
        """Return the SQL fragment for the foreign-key constraint.

        :param field_name: Name of the field being formatted for SQL output.
        :type field_name: UNKNOWN

        :returns: The formatted foreign-key clause.
        :rtype: str
        """
        return (f'REFERENCES {self.table.name}({self.field.name}) '
                f'ON DELETE {self.on_delete} '
                f'ON UPDATE {self.on_update}')


class SQLField:

    """Represent a single SQL field definition.
    """
    @_check_types.do
    def __init__(self, name: str, data_type: str, no_null: bool = False,
                 is_unique: bool = False, default: str | None = None,
                 references: SQLFieldReference | None = None, is_primary: bool = False,
                 autoincrement: bool = True):

        """Initialize the SQL field metadata.

        :param name: Field name.
        :type name: str
        :param data_type: SQL data type string.
        :type data_type: str
        :param no_null: Whether the field forbids ``NULL`` values.
        :type no_null: bool
        :param is_unique: Whether the field must be unique.
        :type is_unique: bool
        :param default: Default SQL literal for the field.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLFieldReference | None
        :param is_primary: Whether the field is the primary key.
        :type is_primary: bool
        :param autoincrement: Whether a primary-key field is engine-generated
            (``AUTOINCREMENT``). Ignored unless ``is_primary`` is ``True`` --
            client-generated primary keys (e.g. UUIDField) set this ``False``.
        :type autoincrement: bool
        """
        self.name = name

        self.type = data_type
        self.default = default
        self.is_unique = is_unique
        self.no_null = no_null
        self.references = references
        self.is_primary = is_primary
        self.autoincrement = autoincrement

        self.parent: SQLTable = None

    @_check_types.do
    def __str__(self):
        """Return the SQL definition fragment for the field.

        :returns: The SQL fragment describing the field.
        :rtype: str
        """
        if self.is_primary:
            primary = ' PRIMARY KEY AUTOINCREMENT' if self.autoincrement else ' PRIMARY KEY'

        else:
            primary = ''
        if self.is_unique:
            unique = ' UNIQUE'
        else:
            unique = ''

        if self.no_null:
            null = ' NOT NULL'
        else:
            null = ''

        if self.default is None:
            default = ''
        else:
            default = f' DEFAULT {self.default}'

        res = f'{self.name} {self.type}{primary}{unique}{default}{null}'

        if self.references is not None:
            res += str(self.references)

        return res

    @_check_types.do
    def is_field_in_table(self, db_cursor, table_name: str):
        """Return whether this field exists in the named table.

        :param db_cursor: Database cursor or connector wrapper used to execute SQL.
        :type db_cursor: UNKNOWN
        :param table_name: Name of the database table to inspect or update.
        :type table_name: str

        :returns: ``True`` when the field exists; otherwise ``False``.
        :rtype: bool
        """
        db_cursor._con.execute(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                               f'pragma_table_info("{table_name}");')

        column_names = eval(db_cursor._con.fetchall()[0][0])

        return self.name in column_names

    @_check_types.do
    def add_to_table(self, db_cursor, table_name: str):

        """Add this field definition to an existing table.

        :param db_cursor: Database cursor or connector wrapper used to execute SQL.
        :type db_cursor: UNKNOWN
        :param table_name: Name of the database table to inspect or update.
        :type table_name: str

        :returns: ``None``.
        :rtype: None
        """
        field = str(self)

        db_cursor._con.execute(f'ALTER TABLE {table_name} ADD COLUMN {field}')
        db_cursor._con.commit()


class PrimaryKeyField(SQLField):

    """Represent an auto-incrementing integer primary-key field.
    """
    @_check_types.do
    def __init__(self, name: str):

        """Initialize the primary-key field definition.

        :param name: Name associated with the object being created.
        :type name: str
        """
        super().__init__(name, FIELD_TYPE_INT, is_primary=True)


class UUIDField(SQLField):

    """Represent a 128-bit, client-generated UUID-style field (16 raw bytes).

    Never engine-generated (no AUTOINCREMENT/AUTO_INCREMENT) -- the value is
    always supplied explicitly on INSERT, whether this field is a primary
    key or a foreign key pointing at one.

    Primary-key usage should leave ``default`` unset (``None``) -- the
    choke-point insert() code always supplies an explicit generated id.
    Foreign-key usage may set ``default="X'00000000000000000000000000000000'"``
    (the nil UUID -- 16 zero bytes) as the not-yet-assigned sentinel, the
    UUID equivalent of the old int scheme's ``default='0'``. The real
    generation mechanism never produces the nil UUID, since a genuine
    timestamp component is always > 0.
    """
    @_check_types.do
    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None,
                 references: SQLFieldReference | None = None, is_primary: bool = False):

        """Initialize the UUID field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param no_null: Whether ``NULL`` values should be disallowed.
        :type no_null: bool
        :param is_unique: Whether the field should enforce unique values.
        :type is_unique: bool
        :param default: Default SQL literal for the field, if any. See class
            docstring -- leave unset for primary-key usage.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLFieldReference | None
        :param is_primary: Whether the field is the primary key.
        :type is_primary: bool
        """
        super().__init__(name, FIELD_TYPE_UUID, no_null, is_unique,
                         default, references, is_primary, autoincrement=False)


class GeneratedField(SQLField):

    """Represent a virtual generated column -- one whose value is always
    derived from an expression over other columns in the same row, never
    stored/written directly and never supplied on INSERT.

    Used for ``project_id`` on migrated ``pjt_*`` tables: rather than
    storing it redundantly, it's derived from the leading 3 bytes of the
    row's own ``id`` (see database/id_generator.py for the bit layout) --
    ``GENERATED ALWAYS AS (substr(id, 1, 3)) VIRTUAL``. Existing
    ``WHERE project_id = ?`` call sites keep working unchanged; only the
    Python-side value passed in needs to switch from an int to the 3-byte
    big-endian prefix (see id_generator.pack_project_row_id).
    """
    @_check_types.do
    def __init__(self, name: str, data_type: str, expression: str):

        """Initialize the generated field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param data_type: SQL data type of the derived value.
        :type data_type: str
        :param expression: SQL expression the column's value is derived from.
        :type expression: str
        """
        super().__init__(name, data_type)
        self.expression = expression

    @_check_types.do
    def __str__(self):
        """Return the SQL definition fragment for the generated column.

        :returns: The SQL fragment describing the field.
        :rtype: str
        """
        return f'{self.name} {self.type} GENERATED ALWAYS AS ({self.expression}) VIRTUAL'


class ProjectIdField(GeneratedField):

    """Represent the derived ``project_id`` column on a migrated ``pjt_*`` table.

    Zero-config, connector-agnostic wrapper around GeneratedField so
    create_database/*.py schema files never need to know the connector-
    specific type string -- matches how PrimaryKeyField/UUIDField etc. are
    already used without exposing raw SQL type literals.
    """
    @_check_types.do
    def __init__(self):
        """Initialize the ``project_id`` generated-column definition.
        """
        super().__init__('project_id', FIELD_TYPE_BLOB, 'substr(id, 1, 3)')


class TextField(SQLField):

    """Represent a text field definition.
    """
    @_check_types.do
    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        """Initialize the text field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param no_null: Whether ``NULL`` values should be disallowed.
        :type no_null: bool
        :param is_unique: Whether the field should enforce unique values.
        :type is_unique: bool
        :param default: Default SQL literal for the field, if any.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLField | None
        """
        super().__init__(name, FIELD_TYPE_TEXT, no_null, is_unique,
                         default, references, False)


class FloatField(SQLField):

    """Represent a floating-point field definition.
    """
    @_check_types.do
    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        """Initialize the floating-point field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param no_null: Whether ``NULL`` values should be disallowed.
        :type no_null: bool
        :param is_unique: Whether the field should enforce unique values.
        :type is_unique: bool
        :param default: Default SQL literal for the field, if any.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLField | None
        """
        super().__init__(name, FIELD_TYPE_REAL, no_null, is_unique,
                         default, references, False)


class BytesField(SQLField):

    """Represent a bytes/blob field definition.
    """
    @_check_types.do
    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        """Initialize the bytes field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param no_null: Whether ``NULL`` values should be disallowed.
        :type no_null: bool
        :param is_unique: Whether the field should enforce unique values.
        :type is_unique: bool
        :param default: Default SQL literal for the field, if any.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLField | None
        """
        super().__init__(name, FIELD_TYPE_BLOB, no_null, is_unique,
                         default, references, False)


class IntField(SQLField):

    """Represent an integer field definition.
    """
    @_check_types.do
    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        """Initialize the integer field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param no_null: Whether ``NULL`` values should be disallowed.
        :type no_null: bool
        :param is_unique: Whether the field should enforce unique values.
        :type is_unique: bool
        :param default: Default SQL literal for the field, if any.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLField | None
        """
        super().__init__(name, FIELD_TYPE_INT, no_null, is_unique,
                         default, references, False)


class BlobField(SQLField):

    """Represent a blob field definition.
    """
    @_check_types.do
    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        """Initialize the blob field definition.

        :param name: Name associated with the object being created.
        :type name: str
        :param no_null: Whether ``NULL`` values should be disallowed.
        :type no_null: bool
        :param is_unique: Whether the field should enforce unique values.
        :type is_unique: bool
        :param default: Default SQL literal for the field, if any.
        :type default: str | None
        :param references: Optional foreign-key reference metadata.
        :type references: SQLField | None
        """
        super().__init__(name, FIELD_TYPE_BLOB, no_null, is_unique,
                         default, references, False)
