# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

import multiprocessing
import queue
import os
import json
import threading
import traceback

from .. import resources as _resources

if TYPE_CHECKING:
    from . import manager as _manager
    from ..database.global_db import image as _image
    from ..database.global_db import resource_state as _resource_state
    from ..database.global_db import datasheet as _datasheet
    from ..database.global_db import cad as _cad


def _process_worker(in_queue: multiprocessing.Queue,
                    out_queue: multiprocessing.Queue,
                    exit_event: multiprocessing.Event,
                    print_lock: multiprocessing.Lock):

    """Download and register missing image resources in a subprocess.

    :param in_queue: Queue containing image identifiers to process.
    :type in_queue: multiprocessing.Queue
    :param out_queue: Queue used to send progress messages back to the parent.
    :type out_queue: multiprocessing.Queue
    :param exit_event: Process event used to coordinate startup and shutdown.
    :type exit_event: multiprocessing.Event
    :param print_lock: Lock used when printing diagnostics.
    :type print_lock: multiprocessing.Lock

    :returns: ``None``.
    :rtype: None
    """
    from . import manager

    exit_event.set()  # signal parent: alive

    while exit_event.is_set():
        pass  # wait for parent to clear

    while in_queue.empty():
        pass

    ppid = in_queue.get_nowait()

    # Regenerate service ID from inherited stealth environment variables
    cred_manager = manager.CredManager(print_lock, pid=ppid)

    credentials = cred_manager.retrieve_credentials(print_lock)
    if credentials is None:
        out_queue.put(json.dumps({'log': 'IMAGE DOWNLOADER: error collecting credentials'}))
        return

    from . import db_broker

    connector = db_broker.connect_to_database(credentials)

    if connector is None:
        out_queue.put(json.dumps({'log': 'IMAGE DOWNLOADER: unknown database type'}))
        return

    while not exit_event.is_set():
        try:
            in_message = in_queue.get()
        except queue.Empty:
            continue

        if in_message is None:
            continue

        db_id = in_message['id']
        type_ = in_message['type']

        out_message = in_message.copy()
        out_message['step'] = 1

        # Step 1: notify parent that work has started; parent already
        # holds the claim and will call update_progress on the DB.
        out_queue.put(out_message)

        if type_ == _resources.RESOURCE_TYPE_CAD:
            table_name = 'cads'
        elif type_ == _resources.RESOURCE_TYPE_DATASHEET:
            table_name = 'datasheets'
        elif type_ == _resources.RESOURCE_TYPE_IMAGE:
            table_name = 'images'
        else:
            out_message['err_no'] = -100
            out_message['err_msg'] = f'Unknown resource type ({type_})'
            out_queue.put(out_message)
            continue

        connector.execute(f'SELECT uuid, path FROM {table_name} WHERE id={db_id};')
        image = connector.fetchall()

        if not image:
            out_message['err_no'] = -500
            out_message['err_msg'] = f'Record foes not exist in table "{table_name}" ({db_id})'
            out_queue.put(out_message)
            continue

        out_message['step'] = 2
        out_queue.put(out_message)

        uuid, path = image[0]

        if uuid is not None or not path:
            out_message['err_no'] = -600
            out_message['err_msg'] = f'Record uuid or path is not correct "{table_name}" ({db_id})'
            out_queue.put(out_message)
            continue

        out_message['step'] = 3
        out_queue.put(out_message)

        try:
            values = _resources.collect_resource(connector, type_, path)

        except _resources.RequestsError as err:
            out_message['err_no'] = err.code
            out_message['err_msg'] = err.__msg__
            out_message['err_path'] = err.url
            tb = traceback.format_exception(err)
            out_message['traceback'] = ''.join(tb)
            out_queue.put(out_message)
            continue
        # catchall for all other resource exceptions
        except _resources.ResourceException as err:
            out_message['err_no'] = err.code  # NOQA
            out_message['err_msg'] = err.__msg__
            out_message['err_path'] = err.path  # NOQA
            tb = traceback.format_exception(err)
            out_message['traceback'] = ''.join(tb)
            out_queue.put(out_message)
            continue
        except Exception as err:
            tb = traceback.format_exception(err)
            out_message['traceback'] = ''.join(tb)
            out_queue.put(out_message)
            continue

        if values is None:
            out_message['err_no'] = -1000
            out_message['err_msg'] = f'This should not occur "{table_name}" ({db_id})'
            out_queue.put(out_message)
            continue

        out_message['step'] = 4
        out_queue.put(out_message)

        file_id, file_type_id = values

        # Only DB write permitted from child: uuid and file_type_id.
        connector.execute(
            f'UPDATE {table_name} SET file_type_id={file_type_id}, uuid="{file_id}" '
            f'WHERE id={db_id};')
        connector.commit()

        out_message['step'] = 5
        out_queue.put(out_message)

    connector.close()


class ProcessWorker:

    def __init__(self, manager: "_manager.ProcessManager",
                 print_lock: multiprocessing.Lock):

        self.manager = manager
        self.exit_event = multiprocessing.Event()
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()
        self.queue = {}

        self.queue_lock = threading.Lock()
        self.running: dict = None

        from .. import app

        self.app = app

        self.process = multiprocessing.Process(
            target=_process_worker,
            args=(self.out_queue, self.in_queue, self.exit_event, print_lock))

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
            raise RuntimeError('image process_worker failed to start within 10 seconds')

        self.exit_event.clear()

        self.out_queue.put(os.getpid())

    @property
    def has_pending(self):
        with self.queue_lock:
            return bool(len(list(self.queue.keys()))) or self.running is not None

    def send(self):
        with self.queue_lock:
            if self.running is None:
                priorities = list(self.queue.keys())

                if not priorities:
                    return

                priority = min(priorities)

                priority_queue = self.queue[priority]

                item = priority_queue.pop(0)

                self.running = item

                if not priority_queue:
                    del self.queue[priority]

                message = item.copy()
                del message['db_obj']
                del message['resource_obj']
                message['id'] = item['db_obj'].db_id

                self.out_queue.put(message)

    def add(self, priority: int, obj_type: int,
            db_obj: Union["_image.Image", "_datasheet.Datasheet", "_cad.CAD"],
            resource_obj: "_resource_state.ResourceState", mfg: str,
            part_number: str, path: str):
        """
        Queue an image identifier for background resource collection.

        :param priority:
        :type priority: UNKNOWN

        :param obj_type:
        :type obj_type: UNKNOWN

        :param db_obj:
        :type db_obj: UNKNOWN

        :param resource_obj:
        :type resource_obj: UNKNOWN

        :param mfg:
        :type mfg: UNKNOWN

        :param part_number:
        :type part_number: UNKNOWN

        :param path:
        :type path: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """

        with self.queue_lock:
            for queued_items in self.queue.values():
                for item in queued_items[:]:
                    if item['db_obj'] == db_obj:
                        if item['priority'] > priority:
                            queued_items.remove(item)
                            break
                        else:
                            return
                else:
                    continue

                break

            if priority not in self.queue:
                self.queue[priority] = []

            self.queue[priority].append(
                {
                    'db_obj': db_obj,
                    'resource_obj': resource_obj,
                    'type': obj_type,
                    'part_number': part_number,
                    'mfg': mfg,
                    'path': path,
                    'priority': priority
                }
            )

    def recv(self):  # NOQA

        if not self.in_queue.empty():
            message = self.in_queue.get_nowait()
            resource_state = self.running['resource_obj']

            if 'err_no' in message:
                if message['err_no'] in (-500, -100, -600, -20):
                    message['allow_retry'] = False

                else:
                    message['allow_retry'] = True

                def _do(rs, msg):
                    rs.set_error(**msg)

                self.app.CallAfter(_do, resource_state, message)

            else:
                if message['step'] == 5:
                    def _do(rs, db_obj):
                        db_obj.set_progress(5)
                        rs.delete()
                        db_obj.download_complete()

                    self.app.CallAfter(_do, resource_state, self.running['db_obj'])
                    self.running = None
                else:
                    def _do(rs, db_obj, step):
                        db_obj.set_progress(step)
                        rs.update_progress(step)

                    self.app.CallAfter(_do, resource_state, self.running['db_obj'], message['step'])

    def reset(self):
        pass

    def stop(self):
        """
        Signal the worker child processes to stop.

        :returns: ``None``.
        :rtype: None
        """
        self.exit_event.set()
        self.out_queue.put(None)

        self.process.join(5.0)
        if self.process.is_alive():
            print('image process is stuck')
