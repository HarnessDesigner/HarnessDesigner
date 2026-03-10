

FIELD_TYPE_REAL = 'REAL'
FIELD_TYPE_TEXT = 'TEXT'
FIELD_TYPE_INT = 'INT'
FIELD_TYPE_BLOB = 'BLOB'

REFERENCE_CASCADE = 'CASCADE'
REFERENCE_DEFAULT = 'SET DEFAULT'


class SQLTable:

    def __init__(self, name: str, *fields: "SQLField"):
        self.name = name
        self.fields = fields

    def is_in_db(self, db_cursor) -> bool:
        db_cursor.execute(f'SELECT name FROM {db_cursor.database_name}.sqlite_master WHERE type="table";')
        rows = db_cursor.fetchall()

        table_names = [row[0] for row in rows]

        return self.name in table_names

    def is_ok(self, db_cursor) -> bool:
        db_cursor(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                  f'pragma_table_info("{self.name}");')

        column_names = eval(db_cursor.fetchall()[0][0])
        for field in self.fields:
            if field.name not in column_names:
                return False

        return True

    def update_fields(self, db_cursor):

        db_cursor(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                  f'pragma_table_info("{self.name}");')

        column_names = eval(db_cursor.fetchall()[0][0])
        for field in self.fields:
            if field.name not in column_names:
                field.add_to_table(db_cursor, self.name)

    def add_to_db(self, db_cursor):
        fields = [str(field) for field in self.fields]

        fields = ', '.join(fields)

        db_cursor.execute(f'CREATE TABLE {self.name} ({fields}); COMMIT;')


class SQLFieldReference:

    def __init__(self, table: SQLTable, field: "SQLField", on_delete=REFERENCE_DEFAULT, on_update=REFERENCE_DEFAULT):
        self.table = table
        self.field = field
        self.on_delete = on_delete
        self.on_update = on_update

    def format(self, field_name):
        return (f'FOREIGN KEY ({field_name}) '
                f'REFERENCES {self.table.name}({self.field.name}) '
                f'ON DELETE {self.on_delete} '
                f'ON UPDATE {self.on_update}')


class SQLField:

    def __init__(self, name: str, data_type: str, no_null: bool = False,
                 is_unique: bool = False, default: str | None = None,
                 references: SQLFieldReference | None = None, is_primary: bool = False):

        self.name = name

        self.type = data_type
        self.default = default
        self.is_unique = is_unique
        self.no_null = no_null
        self.references = references
        self.is_primary = is_primary

        self.parent: SQLTable = None

    def __str__(self):
        if self.is_primary:
            primary = ' PRIMARY KEY AUTOINCREMENT'

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

        res = [f'{self.name} {self.type}{primary}{unique}{default}{null}']

        if self.references is not None:
            res.append(self.references.format(self.name))

        return ', '.join(res)

    def is_field_in_table(self, db_cursor, table_name: str):
        db_cursor(f'SELECT "(\'" || group_concat(name, "\', \'") || "\')" from '
                  f'pragma_table_info("{table_name}");')

        column_names = eval(db_cursor.fetchall()[0][0])

        return self.name in column_names

    def add_to_table(self, db_cursor, table_name: str):
        db_cursor.execute(f'ALTER TABLE {table_name} ADD {str(self)}; COMMIT;')


class PrimaryKeyField(SQLField):

    def __init__(self, name: str):

        super().__init__(name, FIELD_TYPE_INT, no_null=True,
                         is_unique=True, is_primary=True)


class TextField(SQLField):

    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        super().__init__(name, FIELD_TYPE_TEXT, no_null, is_unique,
                         default, references, False)


class FloatField(SQLField):

    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        super().__init__(name, FIELD_TYPE_REAL, no_null, is_unique,
                         default, references, False)


class BytesField(SQLField):

    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        super().__init__(name, FIELD_TYPE_BLOB, no_null, is_unique,
                         default, references, False)


class IntField(SQLField):

    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        super().__init__(name, FIELD_TYPE_INT, no_null, is_unique,
                         default, references, False)


class BlobField(SQLField):

    def __init__(self, name: str, no_null: bool = False, is_unique: bool = False,
                 default: str | None = None, references: SQLField | None = None):

        super().__init__(name, FIELD_TYPE_BLOB, no_null, is_unique,
                         default, references, False)
