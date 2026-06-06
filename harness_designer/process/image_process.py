# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import multiprocessing
import os
import json

import requests.exceptions as _req_exc

if TYPE_CHECKING:
    from . import manager as _manager


def _process_worker(in_queue: multiprocessing.Queue,
                    out_queue: multiprocessing.Queue,
                    exit_event: multiprocessing.Event,
                    print_lock: multiprocessing.Lock,
                    sleep_event: multiprocessing.Event):

    """Download and register missing image resources in a subprocess.

    :param in_queue: Queue containing image identifiers to process.
    :type in_queue: multiprocessing.Queue
    :param out_queue: Queue used to send progress messages back to the parent.
    :type out_queue: multiprocessing.Queue
    :param exit_event: Process event used to coordinate startup and shutdown.
    :type exit_event: multiprocessing.Event
    :param print_lock: Lock used when printing diagnostics.
    :type print_lock: multiprocessing.Lock
    :param sleep_event: Event used to wake the worker when new image work is queued.
    :type sleep_event: multiprocessing.Event

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

    from .. import resources as _resources

    while not exit_event.is_set():
        sleep_event.wait()
        sleep_event.clear()

        while not in_queue.empty():
            if exit_event.is_set():
                break

            image_id = in_queue.get_nowait()

            connector.execute(f'SELECT uuid, path FROM images WHERE id={image_id};')
            image = connector.fetchall()

            if not image:
                continue

            uuid, path = image[0]

            if uuid is not None or not path:
                continue

            # Step 1: notify parent that work has started; parent already
            # holds the claim and will call update_progress on the DB.
            out_queue.put(json.dumps({'id': image_id, 'step': 1}))

            try:
                values = _resources.collect_resource(connector, _resources.IMAGE_TYPE_IMAGE, path)
            except _req_exc.RequestException as req_err:
                _errno = getattr(req_err, 'errno', None)
                if _errno is None:
                    _cause = (getattr(req_err, '__cause__', None) or
                              getattr(req_err, '__context__', None))
                    _errno = getattr(_cause, 'errno', None) if _cause is not None else None
                err_key = (f'{type(req_err).__name__}:{_errno}'
                           if _errno is not None else type(req_err).__name__)
                err_blob = {'message': str(req_err), 'errno': _errno,
                            'image_id': image_id, 'path': path}
                out_queue.put(json.dumps({
                    'id': image_id, 'err_key': err_key, 'err_blob': err_blob,
                    'release': True,
                }))
                continue
            except Exception as err:  # NOQA
                _errno = getattr(err, 'errno', None)
                if _errno is None:
                    _cause = (getattr(err, '__cause__', None) or
                              getattr(err, '__context__', None))
                    _errno = getattr(_cause, 'errno', None) if _cause is not None else None
                err_key = (f'{type(err).__name__}:{_errno}'
                           if _errno is not None else type(err).__name__)
                err_blob = {'message': str(err), 'errno': _errno,
                            'image_id': image_id, 'path': path}
                out_queue.put(json.dumps({
                    'id': image_id, 'err_key': err_key, 'err_blob': err_blob,
                    'release': True,
                }))
                continue

            if values is None:
                out_queue.put(json.dumps({
                    'id': image_id,
                    'err_key': 'step_1',
                    'err_blob': {'message': 'collect_resource returned None',
                                 'image_id': image_id, 'path': path},
                    'release': True,
                }))
                continue

            file_id, file_type_id = values

            out_queue.put(json.dumps({'id': image_id, 'step': 2}))

            # Only DB write permitted from child: uuid and file_type_id.
            connector.execute(
                f'UPDATE images SET file_type_id={file_type_id}, uuid="{file_id}" '
                f'WHERE id={image_id};')
            connector.commit()

            # Step 3: final success; parent updates progress in resource_state.
            out_queue.put(json.dumps({'id': image_id, 'step': 3}))

            sleep_event.wait(2.0)

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
            raise RuntimeError('image process_worker failed to start within 10 seconds')

        self.exit_event.clear()

        self.out_queue.put(os.getpid())

    def send(self, image_id):
        """Queue an image identifier for background resource collection.

        :param image_id: Identifier of the image row to process.
        :type image_id: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        self.out_queue.put(image_id)
        self.sleep_event.set()

    def recv(self):  # NOQA
        if not self.in_queue.empty():
            message = self.in_queue.get_nowait()
            return json.loads(message)
        return None

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
            print('image process is stuck')
