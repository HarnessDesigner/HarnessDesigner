import os
import sqlite3


class ConfigTable:
    """
    This class represents a table in the sqlite database.

    This class mimicks some of the features of a dictionary so the saved
    entries are able to be accessed by using the attaribute name as a key.
    """

    def __init__(self, con, name):
        self._con = con
        self.name = name

    def __contains__(self, item):
        with self._con:
            cur = self._con.cursor()
            cur.execute(f'SELECT id FROM {self.name} WHERE key = "{item}";')
            if cur.fetchall():
                cur.close()
                return True

            cur.close()

        return False

    def __getitem__(self, item):
        with self._con:
            cur = self._con.cursor()
            cur.execute(f'SELECT value FROM {self.name} WHERE key = "{item}";')
            value = cur.fetchall()[0][0]
            cur.close()

        try:
            return eval(value)
        except:  # NOQA
            return value

    def __setitem__(self, key, value):
        value = str(value)

        if key not in self:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'INSERT INTO {self.name} (key, value) VALUES(?, ?);', (key, value))
                self._con.commit()
                cur.close()
        else:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'UPDATE {self.name} SET value = "{value}" WHERE key = "{key}";')

                self._con.commit()
                cur.close()

    def __delitem__(self, key):
        with self._con:
            cur = self._con.cursor()
            cur.execute(f'DELETE FROM {self.name} WHERE key = "{key}"')
            self._con.commit()
            cur.close()


class ConfigDB:
    """
    This class handles the actual connection to the sqlite database.

    Handles what table in the database is to be accessed. The tables are
    not cached because most of the information that is stored only gets loaded
    when the application starts and data gets saved to the database if a value
    gets modified and also when the application exits.
    """

    def __init__(self, app_data):

        import threading

        self.lock = threading.Lock()

        config_db_file = os.path.join(app_data, 'config.db')

        self._con = sqlite3.connect(config_db_file, check_same_thread=False)

    def __contains__(self, item):
        with self._con:
            cur = self._con.cursor()
            cur.execute('SELECT name FROM sqlite_master WHERE type="table";')
            tables = [row[0] for row in cur.fetchall()]
            cur.close()

        return item in tables

    def __getitem__(self, item):
        if item not in self:
            with self._con:
                cur = self._con.cursor()
                cur.execute(f'CREATE TABLE {item}('
                                  'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                                  'key TEXT UNIQUE NOT NULL, '
                                  'value TEXT NOT NULL'
                                  ');')
                self._con.commit()
                cur.close()

        return ConfigTable(self._con, item)

    def close(self):
        self._con.close()
