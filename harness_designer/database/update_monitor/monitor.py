
from typing import TYPE_CHECKING

import multiprocessing
import threading
import sys
import wx
import json

from . import manager as _manager
from ... import config as _config

if TYPE_CHECKING:
    from ... import ui as _ui

Config = _config.Config.database


class BaseConnector:

    def __init__(self, con, cur):
        self._connection = con
        self._cursor = cur

    def execute(self, cmd):
        self._cursor.execute(cmd)

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        try:
            self._cursor.close()
            self._connection.close()
        except:  # NOQA
            pass


class MySQLConnector(BaseConnector):

    def __init__(self, host, port, user, password, database):
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

    def __init__(self, path):
        import sqlite3

        con = sqlite3.connect(path)
        cur = con.cursor()

        super().__init__(con, cur)


def connect_to_database(credentials):
    from .. import db_connectors as _db_connectors

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


def process_worker(in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue,
                   exit_event: multiprocessing.Event, print_lock: multiprocessing.Lock,
                   sleep_event: multiprocessing.Event):

    field_names = {}
    records = {}

    # Regenerate service ID from inherited stealth environment variables
    cred_manager = _manager.Manager()

    credentials = cred_manager.retrieve_credentials()
    if credentials is None:
        with print_lock:
            print('DB MONITOR: eror collecting credentials')

        return

    connector = connect_to_database(credentials)

    if connector is None:
        with print_lock:
            print('DB MONITOR: unknown database type')
        return

    while not exit_event.is_set():
        sleep_event.wait(Config.monitor_duration)
        sleep_event.clear()

        ping_received = False

        while not in_queue.empty():
            message = json.loads(in_queue.get_nowait())

            if message['type'] == 'ping':
                ping_received = True
                out_queue.put(json.dumps({'type': 'pong'}))

            elif message['type'].startswith('field_names_'):
                table_name = message['type'].replace('field_names_', '')
                field_names[table_name] = message['data']

            elif message['type'].startswith('add_'):
                table_name = message['type'].replace('add_', '')
                if table_name not in records:
                    records[table_name] = {}

                data = message['data']

                fields = ', '.join(field_names[table_name])

                db_ids = [f'id={db_id}' for db_id in data]
                db_ids = ' OR '.join(db_ids)
                connector.execute(f'SELECT {fields} WHERE {table_name} WHERE {db_ids};')
                rows = connector.fetchall()
                for row in rows:
                    records[table_name][row[0]] = row

            elif message['type'].startswith('remove_'):
                table_name = message['type'].replace('remove_', '')

                if table_name not in records:
                    records[table_name] = {}

                db_id = message['data']
                records[table_name].pop(db_id, None)

            elif message['type'].startswith('update_'):
                table_name = message['type'].replace('update_', '')

                if table_name not in records:
                    records[table_name] = {}

                db_id = message['data']

                fields = ', '.join(field_names[table_name])

                connector.execute(f'SELECT {fields} WHERE {table_name} WHERE id={db_id};')
                rows = connector.fetchall()

                records[table_name][db_id] = rows[0]

            elif message['type'] == 'reset_storage':
                field_names.clear()
                records.clear()
            else:
                out_queue.put(json.dumps({'type': 'unknown_type', 'data': message['type']}))

        if not ping_received:
            with print_lock:
                print('DB MONITOR: synchronization error with child process')
                break

        for table_name, fields in field_names.items():
            fields = ', '.join(fields)

            if table_name not in records:
                continue

            db_ids = [f'id={db_id}' for db_id in records[table_name].keys()]
            db_ids = ' OR '.join(db_ids)
            connector.execute(f'SELECT {fields} from {table_name} WHERE {db_ids};')
            rows = connector.fetchall()

            db_ids = list(records[table_name].keys())
            for row in rows:
                db_id = row[0]
                db_ids.remove(db_id)
                if records[table_name][db_id] != row:
                    out_queue.put(json.dumps({'type': 'update_' + table_name,
                                              'data': db_id}))

                    records[table_name][db_id] = rows[0]

            for db_id in db_ids:
                out_queue.put(json.dumps({'type': 'remove_' + table_name,
                                          'data': db_id}))

                del records[table_name][db_id]

    connector.close()


class Monitor(threading.Thread):

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        self.process_exit_event = multiprocessing.Event()
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()
        self.print_lock = multiprocessing.Lock()
        self.sleep_event = multiprocessing.Event()

        self.queue_lock = threading.Lock()
        self.exit_event = threading.Event()
        self.queue = []
        self.wait_event = threading.Event()

        threading.Thread.__init__(self, name='db_monitor_thread')
        self.daemon = True

        self.process = multiprocessing.Process(
            target=process_worker, args=(self.out_queue, self.in_queue, self.process_exit_event,
                                         self.print_lock, self.sleep_event))

        self.process.daemon = True

    def start(self):
        self.process.start()
        threading.Thread.start(self)

    def run(self):
        while not self.exit_event.is_set():
            self.wait_event.wait(Config.monitor_duration)
            self.wait_event.clear()

            got_pong = False
            while not self.in_queue.empty():
                message = json.loads(self.in_queue.get_nowait())
                if message['type'] == 'pong':
                    got_pong = True

                if message['type'].startswith('update_'):
                    table_name = message['type'].replace('update_', '')
                    db_id = message['data']

                    wx.CallAfter(self.mainframe.project.update_objects, table_name, db_id)

                elif message['type'].startswith('remove_'):
                    table_name = message['type'].replace('remove_', '')
                    db_id = message['data']

                    wx.CallAfter(self.mainframe.project.update_objects, table_name, db_id)

            if not got_pong:
                self.out_queue.put(json.dumps({'type': 'ping'}))
                self.sleep_event.set()
                self.wait_event.wait(0.01)
                self.wait_event.set()
                continue

            with self.queue_lock:
                messages = self.queue[:]
                del self.queue[:]

            self.out_queue.put(json.dumps({'type': 'ping'}))

            for message in messages:
                self.out_queue.put(message)

            self.sleep_event.set()

    def send(self, **kwargs):
        message = json.dumps(kwargs)
        with self.queue_lock:
            self.queue.append(message)

    def stop(self):
        self.process_exit_event.set()
        self.sleep_event.set()

        self.exit_event.set()
        self.wait_event.set()
