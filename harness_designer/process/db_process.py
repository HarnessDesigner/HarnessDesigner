# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import multiprocessing
import os
import json

from .. import config as _config


if TYPE_CHECKING:
    from . import manager as _manager


Config = _config.Config.database


def _process_worker(in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue,
                    exit_event: multiprocessing.Event, print_lock: multiprocessing.Lock,
                    sleep_event: multiprocessing.Event):

    """Monitor tracked database rows for updates in a subprocess.

    :param in_queue: Queue used to receive messages from the monitor thread.
    :type in_queue: multiprocessing.Queue
    :param out_queue: Queue used to send notifications back to the monitor thread.
    :type out_queue: multiprocessing.Queue
    :param exit_event: Process event used to coordinate startup and shutdown.
    :type exit_event: multiprocessing.Event
    :param print_lock: Lock used when printing diagnostics.
    :type print_lock: multiprocessing.Lock
    :param sleep_event: Event used to wake the worker before the next polling interval.
    :type sleep_event: multiprocessing.Event

    :returns: ``None``.
    :rtype: None
    """
    exit_event.set()  # signal parent: alive and handle duplication succeeded

    while exit_event.is_set():
        pass  # wait for parent to clear before proceeding

    while in_queue.empty():
        pass

    ppid = in_queue.get_nowait()

    field_names = {}
    records = {}

    from . import manager

    # Regenerate service ID from inherited stealth environment variables
    cred_manager = manager.CredManager(print_lock, pid=ppid)

    credentials = cred_manager.retrieve_credentials(print_lock)
    if credentials is None:
        with print_lock:
            print('DB MONITOR: error collecting credentials')

        return

    from . import db_broker

    connector = db_broker.connect_to_database(credentials)

    if connector is None:
        with print_lock:
            print('DB MONITOR: unknown database type')
        return

    while not exit_event.is_set():
        sleep_event.wait(Config.monitor_duration)
        sleep_event.clear()

        while not in_queue.empty():
            if exit_event.is_set():
                break

            message = json.loads(in_queue.get_nowait())

            print(message)

            if message['type'].startswith('field_names_'):
                table_name = message['type'].replace('field_names_', '')
                field_names[table_name] = message['data']

            elif message['type'].startswith('add_'):
                table_name = message['type'].replace('add_', '')

                if table_name not in records:
                    records[table_name] = {}

                data = message['data']
                while None in data:
                    data.remove(None)

                if not data:
                    continue

                fields = ', '.join(field_names[table_name])

                db_ids = [f'id={db_id}' for db_id in data]
                db_ids = ' OR '.join(db_ids)
                connector.execute(f'SELECT {fields} FROM {table_name} WHERE {db_ids};')
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

        for table_name, fields in field_names.items():
            fields = ', '.join(fields)

            if table_name not in records:
                continue

            if not records[table_name]:
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


class ProcessWorker:

    def __init__(self, manager: "_manager.ProcessManager",
                 print_lock: multiprocessing.Lock):

        self.manager = manager
        self.exit_event = multiprocessing.Event()
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()
        self.sleep_event = multiprocessing.Event()

        self.process = multiprocessing.Process(
            target=_process_worker,
            args=(self.out_queue, self.in_queue, self.exit_event, print_lock, self.sleep_event))

        self.process.daemon = True

    def start(self):
        """
        Start the image child process.

        :returns: ``None``.
        :rtype: None
        :raises RuntimeError: Raised when the connector or worker enters an unexpected state.
        """

        self.process.start()
        self.exit_event.wait(timeout=10.0)
        if not self.exit_event.is_set():
            raise RuntimeError('db process_worker failed to start within 10 seconds')

        self.exit_event.clear()

        self.out_queue.put(os.getpid())

    def send(self, message):
        """
        Queue a message.

        :param message: message to send.
        :type message: str

        :returns: ``None``.
        :rtype: None
        """
        self.out_queue.put(message)
        self.sleep_event.set()

    def recv(self):  # NOQA
        if not self.in_queue.empty():
            message = json.loads(self.in_queue.get_nowait())
            if message['type'].startswith('update_'):
                table_name = message['type'].replace('update_', '')
                db_id = message['data']
                return table_name, db_id

            elif message['type'].startswith('remove_'):
                table_name = message['type'].replace('remove_', '')
                db_id = message['data']

                return table_name, db_id

    def reset(self):
        pass

    def stop(self):
        """
        Signal the worker child processes to stop.

        :returns: ``None``.
        :rtype: None
        """
        self.exit_event.set()
        self.sleep_event.set()

        self.process.join(3.0)
        if self.process.is_alive():
            print('db process is stuck')
