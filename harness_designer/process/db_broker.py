# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import config as _config


Config = _config.Config.database


class BaseConnector:

    """Wrap a low-level database connection used by monitor workers.
    """
    def __init__(self, con, cur):
        """Initialize the connection and cursor wrapper.

        :param con: Open database connection.
        :type con: UNKNOWN
        :param cur: Open cursor associated with ``con``.
        :type cur: UNKNOWN
        """
        self._connection = con
        self._cursor = cur

    def execute(self, cmd):
        """Execute a SQL statement with the wrapped cursor.

        :param cmd: SQL command string to execute.
        :type cmd: UNKNOWN

        :returns: The connector-specific cursor result, if one is returned.
        :rtype: UNKNOWN
        """
        self._cursor.execute(cmd)

    def fetchall(self):
        """Fetch all rows from the wrapped cursor.

        :returns: All remaining rows from the cursor.
        :rtype: list[tuple]
        """
        return self._cursor.fetchall()

    def commit(self):
        """Commit the wrapped database transaction.

        :returns: ``None``.
        :rtype: None
        """
        self._connection.commit()

    def close(self):
        """Close the wrapped cursor and connection if possible.

        :returns: ``None``.
        :rtype: None
        """
        try:
            self._cursor.close()
            self._connection.close()
        except:  # NOQA
            pass


class MySQLConnector(BaseConnector):

    """Open a monitor-side connection to a MySQL database.
    """
    def __init__(self, host, port, user, password, database):
        """Initialize the MySQL monitor connector.

        :param host: MySQL host name or address.
        :type host: UNKNOWN
        :param port: MySQL server port.
        :type port: UNKNOWN
        :param user: MySQL user name.
        :type user: UNKNOWN
        :param password: MySQL password.
        :type password: UNKNOWN
        :param database: MySQL database name.
        :type database: UNKNOWN
        """
        import mysql.connector

        con = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            compress=Config.mysql.compress,
            oci_config_file=Config.mysql.oci_config_file,
            oci_config_profile=Config.mysql.oci_config_profile,
            kerberos_auth_mode=Config.mysql.kerberos_auth_mode,
            force_ipv6=Config.mysql.force_ipv6,
            ssl_verify_identity=Config.mysql.ssl_verify_identity,
            ssl_verify_cert=Config.mysql.ssl_verify_cert,
            ssl_key=Config.mysql.ssl_key,
            ssl_disabled=Config.mysql.ssl_disabled,
            ssl_cert=Config.mysql.ssl_cert,
            ssl_ca=Config.mysql.ssl_ca,
            tls_versions=Config.mysql.tls_versions,
            buffered=Config.mysql.buffered,
            write_timeout=Config.mysql.write_timeout,
            read_timeout=Config.mysql.read_timeout,
            connection_timeout=Config.mysql.connection_timeout,
            client_flags=Config.mysql.client_flags,
            sql_mode=Config.mysql.sql_mode,
            auth_plugin=Config.mysql.auth_plugin,
            openid_token_file=Config.mysql.openid_token_file,
            database=database,
        )
        cur = con.cursor()

        super().__init__(con, cur)


class SQLiteConnector(BaseConnector):

    """Open a monitor-side connection to a SQLite database.
    """
    def __init__(self, path):
        """Initialize the SQLite monitor connector.

        :param path: Path to the SQLite database file.
        :type path: UNKNOWN
        """
        import sqlite3

        con = sqlite3.connect(path)
        cur = con.cursor()

        super().__init__(con, cur)


def connect_to_database(credentials):
    """Create a monitor connector from stored credentials.

    :param credentials: Credential dictionary previously stored in the keyring.
    :type credentials: UNKNOWN

    :returns: A connector instance for the supplied credentials.
    :rtype: BaseConnector | None
    """
    from ..database import db_connectors as _db_connectors

    if credentials['type'] == _db_connectors.CONNECTOR_SQLITE:
        return SQLiteConnector(credentials['database_path'])

    elif credentials['type'] == _db_connectors.CONNECTOR_MYSQL:
        return MySQLConnector(
            host=credentials['host'],
            port=credentials['port'],
            user=credentials['user'],
            password=credentials['password'],
            database=credentials['database']
        )



