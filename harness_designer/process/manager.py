# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Keyring-backed credential management for database monitor processes."""


from typing import TYPE_CHECKING


import os
import sys

if sys.platform.startswith('win'):
    os.environ['PYTHON_KEYRING_BACKEND'] = 'keyring.backends.Windows.WinVaultKeyring'


import multiprocessing
import threading
import json
import keyring
import hmac
import hashlib
import secrets
import uuid

from .. import config as _config


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.database


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


class CredManager:

    """Store and recover database credentials for monitor subprocesses.
    """
    def __init__(self, print_lock, pid=None):
        """Initialize the credential manager and derive the service identifier.

        :param print_lock: Lock optionally used for debug output.
        :type print_lock: UNKNOWN
        :param pid: Optional parent process identifier used to recreate a session.
        :type pid: None
        """
        if pid is None:
            # from . import clean_creds as _clean_creds
            #
            # _clean_creds.run()

            self.parent_pid = os.getpid()
        else:
            self.parent_pid = pid

        # with print_lock:
        #     print('parent pid:', self.parent_pid)

        pair_index = self.parent_pid % len(STEALTH_ENV_PAIRS)
        # with print_lock:
        #     print('pair_index:', pair_index)

        self.env_uuid, self.env_token = STEALTH_ENV_PAIRS[pair_index]
        # with print_lock:
        #     print('env_uuid:', self.env_uuid)
        #     print('env_token:', self.env_token)

        if self.env_uuid not in os.environ:
            self.app_uuid = str(uuid.uuid4())

            os.environ[self.env_uuid] = self.app_uuid
            self._is_parent = True
        else:
            self.app_uuid = os.environ[self.env_uuid]
            self._is_parent = False

        # with print_lock:
        #     print('app_uuid:', self.app_uuid)
        #     print('is_parent:', self._is_parent)

        if self.env_token not in os.environ:
            self.secret_token = secrets.token_hex(32)
            os.environ[self.env_token] = self.secret_token
        else:
            self.secret_token = os.environ[self.env_token]

        self.service_id = self._generate_service_id()

        # with print_lock:
        #     print('secret_token:', self.secret_token)
        #     print('service_id:', self.service_id)

    def _generate_service_id(self):
        """Generate the keyring service identifier for the current session.

        :returns: The generated keyring service identifier.
        :rtype: str
        """
        message = f"{self.app_uuid}|{self.parent_pid}".encode('utf-8')

        mac = hmac.new(key=self.secret_token.encode('utf-8'),
                       msg=message,
                       digestmod=hashlib.sha256).hexdigest()

        uuid_prefix = self.app_uuid.replace('-', '')[:8]
        hmac_prefix = mac[:16]

        return f"session_{uuid_prefix}_{hmac_prefix}"

    def get_app_uuid(self):
        """Return the application UUID used for this credential session.

        :returns: The application UUID associated with the current credential session.
        :rtype: str
        """
        return self.app_uuid

    def store_credentials(self, print_lock, db_type, **kwargs):
        """Store connector credentials for the requested database type.

        :param print_lock: Lock optionally used for debug output.
        :type print_lock: UNKNOWN
        :param db_type: Connector type constant identifying the credentials being stored.
        :type db_type: UNKNOWN
        :param kwargs: Connector-specific credential values.
        :type kwargs: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        from ..database import db_connectors as _db_connectors

        if db_type == _db_connectors.CONNECTOR_SQLITE:
            self.store_sqlite_credentials(print_lock, **kwargs)

        elif db_type == _db_connectors.CONNECTOR_MYSQL:
            self.store_mysql_credentials(print_lock, **kwargs)

    def store_sqlite_credentials(self, print_lock, database_path):
        # with print_lock:
        #     print('database_path:', database_path)

        """Store SQLite monitor credentials in the keyring.

        :param print_lock: Lock optionally used for debug output.
        :type print_lock: UNKNOWN
        :param database_path: Path to the SQLite database file.
        :type database_path: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        keyring.set_password(self.service_id, "db_type", "sqlite")
        keyring.set_password(self.service_id, "sqlite_path", database_path)

    def store_mysql_credentials(self, print_lock, host, port, user, password, database):
        # with print_lock:
        #     print('host:', host)

        """Store MySQL monitor credentials in the keyring.

        :param print_lock: Lock optionally used for debug output.
        :type print_lock: UNKNOWN
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

        :returns: ``None``.
        :rtype: None
        """
        keyring.set_password(self.service_id, "db_type", "mysql")
        keyring.set_password(self.service_id, "mysql_host", host)
        keyring.set_password(self.service_id, "mysql_port", str(port))
        keyring.set_password(self.service_id, "mysql_user", user)
        keyring.set_password(self.service_id, "mysql_password", password)
        keyring.set_password(self.service_id, "mysql_database", database)

    def retrieve_credentials(self, print_lock):
        """Retrieve stored credentials for the current monitor session.

        :param print_lock: Lock optionally used for debug output.
        :type print_lock: UNKNOWN

        :returns: The recovered credential mapping, or ``None`` when no credentials are stored.
        :rtype: dict | None
        :raises ValueError: Raised when stored credential data is incomplete or invalid.
        """
        from ..database import db_connectors as _db_connectors

        db_type = keyring.get_password(self.service_id, "db_type")
        # with print_lock:
        #     print('db_type:', db_type)

        if db_type is None:
            return None

        if db_type == "sqlite":
            db_path = keyring.get_password(self.service_id, "sqlite_path")
            # with print_lock:
            #     print('db_path:', db_path)

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
        """Remove stored credentials and related environment variables.

        :returns: ``None``.
        :rtype: None
        """
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


class ProcessManager(threading.Thread):

    """Coordinate background database monitoring for the main UI thread.
    """
    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialize monitor threads, queues, and subprocesses.

        :param mainframe: Main application frame that receives update notifications.
        :type mainframe: '_ui.MainFrame'
        """
        self.mainframe = mainframe
        self._print_lock = multiprocessing.Lock()
        self._db_queue_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._exit_event = threading.Event()
        self._db_queue = []
        self._wait_event = threading.Event()
        self._core_count = os.cpu_count()
        self.wait_duration = Config.monitor_duration
        self._model_process_active = 0

        if self._core_count < 4:
            from ..ui.dialogs import error as _error

            dlg = _error.ErrorDialog(
                self.mainframe,
                'Application needs a minimim of 4 cpu cores to run.',
                'Core Count Error')

            dlg.exec()

            self.mainframe.close()
            sys.exit(1)

        from . import db_process
        from . import image_process
        from . import model_process

        self._db_process = db_process.ProcessWorker(self, self._print_lock)
        self._image_process = image_process.ProcessWorker(self, self._print_lock)
        self._model_processes = [model_process.ProcessWorker(self, self._print_lock)]
        self._model_processes_cb = [None]
        self._model_progress = {}

        threading.Thread.__init__(self, name='process_monitor_thread')
        self.daemon = True

    def start(self):
        """Start the monitor subprocesses and worker thread.

        :returns: ``None``.
        :rtype: None
        :raises RuntimeError: Raised when the connector or worker enters an unexpected state.
        """
        self._db_process.start()
        self._image_process.start()
        self._model_processes[0].start(True)

        threading.Thread.start(self)

    def get_image(self, image_id):
        """Queue an image identifier for background resource collection.

        :param image_id: Identifier of the image row to process.
        :type image_id: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        self._image_process.send(image_id)

    def run(self):
        """Forward monitor subprocess messages back to the UI thread.

        :returns: ``None``.
        :rtype: None
        """
        from harness_designer import app as _app

        curr_progress_index = 0
        curr_progresses = []
        start_progress = False

        while not self._exit_event.is_set():
            got_message = False

            with self._model_lock:
                offset = 0
                for i, process in enumerate(self._model_processes[:]):
                    message = process.recv()

                    if message is None:
                        continue

                    got_message = True

                    if 'watchdog_restart' in message:
                        with self._print_lock:
                            print('MODEL PROCESS MESSAGE:', message)

                        self._model_processes_cb[i - offset] = None
                        is_primary = message['is_primary']

                        from ..ui.dialogs import error as _error

                        def _do(msg):
                            dlg = _error.ErrorDialog(
                                self.mainframe,
                                json.dumps(msg, indent=4),
                                '3D Model Conversion Watchdog timeout')

                            dlg.exec()

                        _app.CallAfter(_do, message)

                        del self._model_progress[message['part_number']]
                        self._model_process_active -= 1
                        if part_number in curr_progresses:
                            index = curr_progresses.index(part_number)

                            if curr_progress_index >= index:
                                curr_progress_index -= 1

                            curr_progresses.remove(part_number)

                        if not self._model_process_active:
                            def _do():
                                self.mainframe.end_progress_bar()

                            _app.CallAfter(_do)

                        if is_primary:
                            from . import model_process

                            self._model_processes[i - offset] = model_process.ProcessWorker(self, self._print_lock)
                            self._model_processes[i - offset].start(True)
                        else:
                            self._model_processes.remove(process)
                            self._model_processes_cb.pop(i - offset)
                            offset += 1

                        continue

                    if 'exit_loop' in message:
                        self._model_processes.remove(process)
                        self._model_processes_cb.pop(i - offset)
                        offset += 1
                        continue

                    if 'err' in message:
                        with self._print_lock:
                            print('MODEL PROCESS MESSAGE:', message)

                        from ..ui.dialogs import error as _error

                        def _do(msg):
                            dlg = _error.ErrorDialog(
                                self.mainframe,
                                json.dumps(msg, indent=4),
                                '3D Model Conversion Error')

                            dlg.exec()

                        _app.CallAfter(_do, message)
                        self._model_process_active -= 1
                        self._model_processes_cb[i - offset] = None
                        del self._model_progress[message['part_number']]

                        if part_number in curr_progresses:
                            index = curr_progresses.index(part_number)

                            if curr_progress_index >= index:
                                curr_progress_index -= 1

                            curr_progresses.remove(part_number)

                        if not self._model_process_active:
                            def _do():
                                self.mainframe.end_progress_bar()

                            _app.CallAfter(_do)
                            start_progress = False

                        continue
                    else:
                        step = message['step']
                        part_number = message['part_number']

                        def _do(stp, pn, start):
                            if start:
                                self.mainframe.start_progress('', 10)

                            self.mainframe.set_progress(stp, pn)

                        if step == 0:
                            curr_progresses.insert(curr_progress_index, part_number)
                            if not self._model_progress:
                                start_progress = True

                        self._model_progress[part_number] = step

                        if step == 10:
                            index = curr_progresses.index(part_number)
                            if curr_progress_index >= index:
                                curr_progress_index -= 1

                            curr_progresses.remove(part_number)
                            del self._model_progress[part_number]

                            def _do2(cb, db_id):
                                model3d_obj = self.mainframe.global_db.models3d_table[db_id]
                                model3d_obj.load('', '', cb)

                            _app.CallAfter(_do2, self._model_processes_cb[i - offset], message['id'])

                            self._model_processes_cb[i - offset] = None

                            self._model_process_active -= 1

                            if self._model_process_active:
                                start_progress = True

                        _app.CallAfter(_do, step, part_number, start_progress)

                        start_progress = False

            if got_message:
                continue

            if self._model_process_active:
                self.wait_duration = 5
                curr_progress_index += 1

                if curr_progress_index > len(curr_progresses) - 1:
                    curr_progress_index = 0
                    
                if curr_progresses:
                    part_number = curr_progresses[curr_progress_index]
                    step = self._model_progress[part_number]

                    def _do(pn, stp):
                        self.mainframe.set_progress(stp, pn)

                    _app.CallAfter(_do, part_number, step)
            else:
                self.wait_duration = Config.monitor_duration

            self._wait_event.wait(self.wait_duration)
            self._wait_event.clear()

            args = self._db_process.recv()

            while args is not None:
                _app.CallAfter(self.mainframe.project.update_objects, *args)
                args = self._db_process.recv()

            with self._db_queue_lock:
                messages = self._db_queue[:]
                del self._db_queue[:]

            for message in messages:
                self._db_process.send(message)

    def reset(self):
        """Clear cached monitor state in the worker process.

        :returns: ``None``.
        :rtype: None
        """
        self.send(type='reset_storage')

    def get_model(self, callback, **model_info):
        message = json.dumps(model_info)

        with self._model_lock:
            for i, process in enumerate(self._model_processes[:]):

                if not process.is_alive():
                    continue

                if self._model_processes_cb[i] is None:
                    self._model_process_active += 1
                    process.send(message)
                    self._model_processes_cb[i] = callback
                    break
            else:
                if len(self._model_processes) == self._core_count:
                    from ..ui.dialogs import error as _error

                    dlg = _error.ErrorDialog(
                        self.mainframe,
                        'Unable to queue another model conversion, not enough cpu cores.\n\n'
                        'Please wait until current model conversions are finished processing.',
                        'CPU Core Count Error')

                    dlg.exec()
                    return

                from . import model_process

                self._model_process_active += 1
                process = model_process.ProcessWorker(self, self._print_lock)
                process.start(False)

                process.send(message)
                self._model_processes.append(process)
                self._model_processes_cb.append(callback)

            self.wait_duration = 5
            self._wait_event.set()

    def send(self, **kwargs):
        """Queue a message for delivery to the worker process.

        :param kwargs: Additional credential fields to persist.
        :type kwargs: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        message = json.dumps(kwargs)
        with self._db_queue_lock:
            self._db_queue.append(message)

        self._wait_event.set()

    def stop(self):
        """Signal the worker thread and subprocesses to stop.

        :returns: ``None``.
        :rtype: None
        """

        for process in self._model_processes[:]:
            process.stop()

        self._image_process.stop()
        self._db_process.stop()
