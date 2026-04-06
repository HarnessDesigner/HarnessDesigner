
import keyring
import os
import hmac
import hashlib
import secrets
import uuid


# Stealth environment variable names (look like system variables)
ENV_SESSION_ID = "XDG_SESSION_TOKEN"      # Looks like X11/desktop session var
ENV_RUNTIME_ID = "DBUS_RUNTIME_UUID"      # Looks like DBus identifier
ENV_DISPLAY_KEY = "DISPLAY_AUTH_KEY"      # Looks like X11 auth
ENV_LOCALE_SEED = "LC_RANDOM_SEED"        # Looks like locale setting

# Alternative stealth names (pick different ones each run for more paranoia):
STEALTH_ENV_PAIRS = [
    ("XDG_SESSION_TOKEN", "DBUS_RUNTIME_UUID"),
    ("DISPLAY_AUTH_KEY", "LC_RANDOM_SEED"),
    ("GTK_THEME_VARIANT", "QT_STYLE_OVERRIDE"),
    ("FONTCONFIG_TIMESTAMP", "PANGO_RC_VARIANT"),
    ("PULSE_COOKIE_ID", "ALSA_CONFIG_UUID"),
    ("SYSTEMD_UNIT_ID", "JOURNAL_STREAM_ID"),
    ("TMPDIR_SESSION_ID", "XDG_CACHE_TOKEN"),
]


class Manager:

    def __init__(self):
        self.parent_pid = os.getpid()

        pair_index = self.parent_pid % len(STEALTH_ENV_PAIRS)
        self.env_uuid, self.env_token = STEALTH_ENV_PAIRS[pair_index]

        if self.env_uuid not in os.environ:
            self.app_uuid = str(uuid.uuid4())

            os.environ[self.env_uuid] = self.app_uuid
            self._is_parent = True
        else:
            self.app_uuid = os.environ[self.env_uuid]
            self._is_parent = False

        if self.env_token not in os.environ:
            self.secret_token = secrets.token_hex(32)
            os.environ[self.env_token] = self.secret_token
        else:
            self.secret_token = os.environ[self.env_token]

        self.service_id = self._generate_service_id()

    def _generate_service_id(self):
        message = f"{self.app_uuid}|{self.parent_pid}".encode('utf-8')

        mac = hmac.new(key=self.secret_token.encode('utf-8'),
                       msg=message,
                       digestmod=hashlib.sha256).hexdigest()

        uuid_prefix = self.app_uuid.replace('-', '')[:8]
        hmac_prefix = mac[:16]

        return f"session_{uuid_prefix}_{hmac_prefix}"

    def get_app_uuid(self):
        return self.app_uuid

    def store_credentials(self, db_type, **kwargs):
        from .. import db_connectors as _db_connectors

        if db_type == _db_connectors.CONNECTOR_SQLITE:
            self.store_sqlite_credentials(**kwargs)

        elif db_type == _db_connectors.CONNECTOR_MYSQL:
            self.store_mysql_credentials(**kwargs)

    def store_sqlite_credentials(self, database_path):
        keyring.set_password(self.service_id, "db_type", "sqlite")
        keyring.set_password(self.service_id, "sqlite_path", database_path)

    def store_mysql_credentials(self, host, port, user, password, database):
        keyring.set_password(self.service_id, "db_type", "mysql")
        keyring.set_password(self.service_id, "mysql_host", host)
        keyring.set_password(self.service_id, "mysql_port", str(port))
        keyring.set_password(self.service_id, "mysql_user", user)
        keyring.set_password(self.service_id, "mysql_password", password)
        keyring.set_password(self.service_id, "mysql_database", database)

    def retrieve_credentials(self):
        from .. import db_connectors as _db_connectors

        db_type = keyring.get_password(self.service_id, "db_type")

        if db_type is None:
            return None

        if db_type == "sqlite":
            db_path = keyring.get_password(self.service_id, "sqlite_path")
            return dict(type=_db_connectors.CONNECTOR_SQLITE,
                        database_path=db_path)

        elif db_type == "mysql":
            password = keyring.get_password(self.service_id, "mysql_password")

            if password is None:
                raise ValueError("MySQL password not found in keyring")

            return dict(type=_db_connectors.CONNECTOR_MYSQL,
                        host=keyring.get_password(self.service_id, "mysql_host"),
                        port=int(keyring.get_password(self.service_id, "mysql_port")),
                        user=keyring.get_password(self.service_id, "mysql_user"),
                        password=password,
                        database=keyring.get_password(self.service_id, "mysql_database"))

    def cleanup(self):
        if not self._is_parent:
            return

        db_type = keyring.get_password(self.service_id, "db_type")

        if db_type is None:
            return

        keyring.delete_password(self.service_id, "db_type")

        if db_type == "sqlite":
            keyring.delete_password(self.service_id, "sqlite_path")

        elif db_type == "mysql":
            keyring.delete_password(self.service_id, "mysql_host")
            keyring.delete_password(self.service_id, "mysql_port")
            keyring.delete_password(self.service_id, "mysql_user")
            keyring.delete_password(self.service_id, "mysql_password")
            keyring.delete_password(self.service_id, "mysql_database")

        if self.env_uuid in os.environ:
            del os.environ[self.env_uuid]
        if self.env_token in os.environ:
            del os.environ[self.env_token]
