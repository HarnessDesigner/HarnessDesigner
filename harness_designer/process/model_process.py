# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import multiprocessing
import os
import json
import numpy as np

import pyfqmr
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from OCP.Vrml import Vrml_Provider
from OCP.STEPControl import STEPControl_Reader
from OCP.IGESControl import IGESControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS

from .. import utils as _utils
from .. import model_data as _model_data


os.environ['PATH'] = os.path.dirname(__file__) + ';' + os.environ['PATH']

import pyassimp  # NOQA


if TYPE_CHECKING:
    from . import manager as _manager


class ModelException(Exception):
    """Represent a model exception in :mod:`harness_designer.database.global_db.model3d.loader`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    pass


class ModelLoadError(ModelException):
    """Represent a model load error in :mod:`harness_designer.database.global_db.model3d.loader`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    pass


def _ocp_read_shape(shape):
    print('tesselating model')

    BRepMesh_IncrementalMesh(
        theShape=shape, theLinDeflection=0.001,
        isRelative=True, theAngDeflection=0.1, isInParallel=True
    )

    vertices = []
    faces = []
    offset = 0

    anExpSF = TopExp_Explorer(shape, TopAbs_FACE)
    while anExpSF.More():
        aLoc = TopLoc_Location()
        poly_triangulation = BRep_Tool.Triangulation_s(
            TopoDS.Face_s(anExpSF.Current()), aLoc)

        if not poly_triangulation:
            anExpSF.Next()   # ← must advance before skipping
            continue

        trsf = aLoc.Transformation()
        node_count = poly_triangulation.NbNodes()

        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            vertices.append((gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z()))

        facet_reversed = anExpSF.Current().Orientation() == TopAbs_REVERSED
        order = [1, 3, 2] if facet_reversed else [1, 2, 3]

        # Use index access instead of Triangles() iterator — more reliable across OCP versions
        for i in range(1, poly_triangulation.NbTriangles() + 1):
            tri = poly_triangulation.Triangle(i)
            faces.append([tri.Value(j) + offset - 1 for j in order])

        offset += node_count
        anExpSF.Next()

    vertices = np.array(vertices, dtype=np.float32)
    faces = np.array(faces, dtype=np.int32)

    print('finished tesselating')
    return vertices, faces


def _load_with_assimp(path):
    """Load the with assimp.

    UNKNOWN details are inferred from the callable name and signature.

    :param path: Filesystem path.
    :type path: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    flags = (pyassimp.postprocess.aiProcess_Triangulate |
             pyassimp.postprocess.aiProcess_JoinIdenticalVertices)

    vertices = []
    faces = []
    offset = 0

    with pyassimp.load(path, processing=flags) as scene:
        for mesh in scene.meshes:
            v = mesh.vertices.copy()
            vertices.append(v)
            faces.append(mesh.faces.copy() + offset)
            offset += len(v)

    vertices = np.array(vertices, dtype=np.float32).reshape(-1, 3)
    faces = np.array(faces, dtype=np.int32).reshape(-1, 3)

    return vertices, faces


def _load_vrml(file):
    """Load the vrml.

    UNKNOWN details are inferred from the callable name and signature.

    :param file: Value for ``file``.
    :type file: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    reader = Vrml_Provider()
    reader.ReadFile(file)
    reader.TransferRoots()
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return vertices, faces


def _load_step(file):
    """Load the step.

    UNKNOWN details are inferred from the callable name and signature.

    :param file: Value for ``file``.
    :type file: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    print('loading step file:', file)
    step_reader = STEPControl_Reader()
    step_reader.ReadFile(file)
    step_reader.TransferRoots()  # NOQA
    shape = step_reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return vertices, faces


def _load_iges(file):
    """Load the iges.

    UNKNOWN details are inferred from the callable name and signature.

    :param file: Value for ``file``.
    :type file: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    reader = IGESControl_Reader()
    reader.ReadFile(file)
    reader.TransferRoots()  # NOQA
    shape = reader.Shape()

    vertices, faces = _ocp_read_shape(shape)

    return vertices, faces


def _load(file: str) -> tuple[np.ndarray, np.ndarray]:
    """Execute the load operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param file: Value for ``file``.
    :type file: str
    :returns: Return value. UNKNOWN details.
    :rtype: tuple[np.ndarray, np.ndarray]
    :raises ModelLoadError: Raised when the operation cannot be completed.
    """
    if file.endswith('.vrml') or file.endswith('wrl'):
        vertices, faces = _load_vrml(file)
    elif file.endswith('.iges') or file.endswith('.igs'):
        vertices, faces = _load_iges(file)
    elif file.endswith('.step') or file.endswith('stp'):
        vertices, faces = _load_step(file)
    else:
        try:
            vertices, faces = _load_with_assimp(file)
        except Exception as err:
            raise ModelLoadError from err

    return vertices, faces


def _center_model(vertices):

    # this code block makes sure the model has 0, 0 as the center of
    # the model. I have found that the models that are loaded from
    # the manufacturers don't always have 0, 0 as the center of the model
    # and for alignment of objects we need to make sure that the centers are
    # used.
    vertices_reshaped = vertices.reshape(-1, 3)
    centroid = vertices_reshaped.mean(axis=0)
    vertices_reshaped -= centroid
    vertices_reshaped = vertices_reshaped.ravel()

    return vertices_reshaped.reshape(-1, 3)


# If the user has a GPU that doesn't have a large amount of
# memory available or the GPU doesn't have a lot of processing power
# the user has the ability to reduce the quality by reducing the number
# of vertices a model has. This will shrink the amount of memory used
# on the GPU as well as increasing the speed in which the GPU renders
# a model
def _reduce_triangles(
    verts: np.ndarray, faces: np.ndarray, target_count: int,
    aggressiveness: float, update_rate: int = 1,
    max_iterations: int = 150, lossless: bool = False,
    threshold_lossless: float = 1e-3, alpha: float = 1e-9,
    K: int = 3
) -> tuple[np.ndarray, np.ndarray]:

    """
    target_count : int
        Target number of triangles, not used if lossless is True
    update_rate : int
        Number of iterations between each update.
        If lossless flag is set to True, rate is 1
    aggressiveness : float
        Parameter controlling the growth rate of the threshold at each
        iteration when lossless is False.
    max_iterations : int
        Maximal number of iterations
    verbose : bool
        control verbosity
    lossless : bool
        Use the lossless simplification method
    threshold_lossless : float
        Maximal error after which a vertex is not deleted, only for
        lossless method.
    alpha : float
        Parameter for controlling the threshold growth
    K : int
        Parameter for controlling the thresold growth
    preserve_border : Bool
        Flag for preserving vertices on open border
    """

    mesh_simplifier = pyfqmr.Simplify()
    mesh_simplifier.setMesh(verts, faces)
    mesh_simplifier.simplify_mesh(
        target_count=target_count,
        update_rate=update_rate,
        max_iterations=max_iterations,
        aggressiveness=aggressiveness,
        lossless=lossless,
        threshold_lossless=threshold_lossless,
        alpha=alpha,
        K=K,
        verbose=False
    )

    vertices, faces, _ = mesh_simplifier.getMesh()

    vertices = vertices.reshape(-1, 3)
    faces = faces.reshape(-1, 3)

    return vertices, faces


import threading


class ThreadWorker(threading.Thread):

    def __init__(self, func, *args):
        self.func = func
        self.args = args

        threading.Thread.__init__(self)
        self.daemon = True
        self.result = None
        self.exception = None

    def run(self):
        try:
            self.result = self.func(*self.args)
        except Exception as err:  # NOQA
            self.exception = err


def _process_worker(in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue,
                    exit_event: multiprocessing.Event, print_lock: multiprocessing.Lock,
                    sleep_event: multiprocessing.Event):

    """
    Downloads and converts the models

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
        pass  # wait for parent to clear

    while in_queue.empty():
        pass

    ppid = in_queue.get_nowait()

    while in_queue.empty():
        pass

    is_primary = in_queue.get_nowait()

    from . import manager

    # Regenerate service ID from inherited stealth environment variables
    cred_manager = manager.CredManager(print_lock, pid=ppid)

    credentials = cred_manager.retrieve_credentials(print_lock)
    if credentials is None:
        with print_lock:
            print('MODEL DOWNLOADER: error collecting credentials')

        return

    from . import db_broker

    from .. import resources as _resources
    from .. import config as _config
    from ..database.create_database import resource_state as _rs

    while not exit_event.is_set():
        if is_primary:
            sleep_event.wait()
        else:
            sleep_event.wait(120)

        if not sleep_event.is_set():
            break

        sleep_event.clear()

        while not in_queue.empty():
            if exit_event.is_set():
                break

            in_message_ = in_queue.get_nowait()
            in_message_ = json.loads(in_message_)

            def _do(in_message):
                import requests.exceptions as _req_exc

                connector = db_broker.connect_to_database(credentials)

                if connector is None:
                    raise RuntimeError('database connection error')

                model_id = in_message['id']
                mfg = in_message['mfg']
                part_number = in_message['part_number']
                model_dir = in_message['model_dir']

                message = {'step': 0, 'id': model_id, 'mfg': mfg, 'part_number': part_number}

                # --- Resource-state coordination ---
                # Guarantee a state row exists (idempotent on existing rows).
                _rs.ensure_row(connector, _rs.RESOURCE_TYPE_MODEL, model_id)

                if not _rs.try_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id):
                    # Another seat has already claimed this model – skip without
                    # doing duplicate work.
                    with print_lock:
                        print(f'MODEL DOWNLOADER: model {model_id} already claimed, skipping')
                    connector.close()
                    return

                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                connector.execute(f'SELECT target_count, aggressiveness, update_rate, iterations, simplify, path FROM models3d WHERE id={model_id};')
                model_data = connector.fetchall()

                if not model_data:
                    err_key = 'step_0'
                    err_blob = {'message': 'invalid database row', 'model_id': model_id, 'mfg': mfg, 'part_number': part_number, 'step': 0}
                    _rs.persist_error(connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                    _rs.release_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id)

                    message = {'err': 'invalid database row',
                               'id': model_id,
                               'mfg': mfg, 'part_number': part_number}

                    out_queue.put(json.dumps(message))
                    connector.close()
                    return

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 1)
                message['step'] = 1
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                target_count, aggressiveness, update_rate, iterations, simplify, path = model_data[0]

                if not path:
                    err_key = 'step_1'
                    err_blob = {'message': 'invalid model url/path', 'model_id': model_id, 'mfg': mfg, 'part_number': part_number, 'step': 1}
                    _rs.persist_error(connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                    _rs.release_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id)

                    message['err'] = 'invalid model url/path'
                    out_queue.put(json.dumps(message))
                    connector.close()
                    return

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 2)
                message['step'] = 2
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                try:
                    file_path = _resources.collect_resource(connector, _resources.IMAGE_TYPE_MODEL, path)
                except _req_exc.RequestException as req_err:
                    err_key = type(req_err).__name__
                    err_blob = {'message': str(req_err), 'model_id': model_id, 'mfg': mfg, 'part_number': part_number, 'step': 2}
                    _rs.persist_error(connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                    _rs.release_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id)
                    message['err'] = f'{err_key}: {req_err}'
                    out_queue.put(json.dumps(message))
                    connector.close()
                    return

                if file_path is None:
                    err_key = 'step_2'
                    err_blob = {'message': 'unable to load model', 'model_id': model_id, 'mfg': mfg, 'part_number': part_number, 'step': 2}
                    _rs.persist_error(connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                    _rs.release_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id)

                    message['err'] = 'unable to load model'
                    out_queue.put(json.dumps(message))
                    connector.close()
                    return

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 3)
                message['step'] = 3
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                model_path, file_type_id = file_path

                connector.execute(f'SELECT extension FROM file_types WHERE id={file_type_id};')
                rows = connector.fetchall()

                if not rows:
                    err_key = 'step_3'
                    err_blob = {'message': 'unsupported file type', 'model_id': model_id, 'mfg': mfg, 'part_number': part_number, 'step': 3}
                    _rs.persist_error(connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                    _rs.release_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id)

                    message['err'] = f'unsupported file type'
                    out_queue.put(json.dumps(message))
                    connector.close()
                    return

                ext = rows[0][0]

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 4)
                message['step'] = 4
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                if not os.path.exists(model_path):
                    err_key = 'step_4'
                    err_blob = {'message': f'file does not exist ("{model_path}")', 'model_id': model_id, 'mfg': mfg, 'part_number': part_number, 'step': 4}
                    _rs.persist_error(connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                    _rs.release_claim(connector, _rs.RESOURCE_TYPE_MODEL, model_id)

                    message['err'] = f'file does not exist ("{model_path}")'
                    out_queue.put(json.dumps(message))
                    connector.close()
                    return

                vertices, faces = _load(model_path)

                vertices = _center_model(vertices)

                if simplify:
                    _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 5)
                    message['step'] = 5
                    out_queue.put(json.dumps(message))

                    if exit_event.is_set():
                        connector.close()
                        return

                    vertices, faces = _reduce_triangles(vertices, faces, target_count, aggressiveness, iterations)

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 6)
                message['step'] = 6
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                vertices, smooth_normals, face_normals, _ = (
                    _utils.compute_normals(vertices, faces))

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 7)
                message['step'] = 7
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                model_data = _model_data.ModelData(vertices, smooth_normals, face_normals)

                uuid = model_data.uuid
                model_data.source_location = path
                model_data.source_type = ext
                model_data.part_number = part_number
                model_data.manufacturer = mfg

                model_data.save(model_dir)

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 8)
                message['step'] = 8
                out_queue.put(json.dumps(message))

                if exit_event.is_set():
                    connector.close()
                    return

                connector.execute(f'UPDATE models3d SET file_type_id={file_type_id}, uuid="{uuid}" WHERE id={model_id};')
                connector.commit()

                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 9)
                message['step'] = 9
                out_queue.put(json.dumps(message))

                os.remove(model_path)

                # Final success: advance to step 10; error data is preserved
                # intentionally so admins can detect client-specific failures
                # even when another seat later succeeded.
                _rs.update_progress(connector, _rs.RESOURCE_TYPE_MODEL, model_id, 10)
                message['step'] = 10
                out_queue.put(json.dumps(message))

                connector.close()

            timeout = _config.Config.resources.model_watchdog_timeout
            import time

            thread = ThreadWorker(_do, in_message_)
            start_time = time.time()

            thread.start()

            stop_time = time.time()
            while stop_time - start_time <= timeout:
                if exit_event.is_set():
                    break

                if thread.is_alive():
                    exit_event.wait(1)
                else:
                    break

                stop_time = time.time()

            if exit_event.is_set():
                break

            if thread.exception is not None:
                # Classify and persist the unhandled error; then release so
                # another seat (or this seat on restart) can retry.
                try:
                    wdog_connector = db_broker.connect_to_database(credentials)
                    if wdog_connector is not None:
                        model_id = in_message_['id']
                        err_key = type(thread.exception).__name__

                        err_blob = {
                            'message': str(thread.exception),
                            'model_id': model_id,
                            'mfg': in_message_.get('mfg'),
                            'part_number': in_message_.get('part_number'),
                        }
                        _rs.persist_error(wdog_connector, _rs.RESOURCE_TYPE_MODEL, model_id, err_key, err_blob)
                        _rs.release_claim(wdog_connector, _rs.RESOURCE_TYPE_MODEL, model_id)
                        wdog_connector.close()
                except Exception:  # NOQA
                    pass

                in_message_['err'] = str(thread.exception)
                out_queue.put(json.dumps(in_message_))
                continue

            if stop_time - start_time > timeout:
                # Watchdog timeout: persist as a blocking issue so no seat
                # auto-retries until an admin clears blocking_issue.
                try:
                    wdog_connector = db_broker.connect_to_database(credentials)
                    if wdog_connector is not None:
                        model_id = in_message_['id']
                        err_blob = {
                            'message': 'watchdog timeout',
                            'model_id': model_id,
                            'mfg': in_message_.get('mfg'),
                            'part_number': in_message_.get('part_number'),
                            'timeout_seconds': timeout,
                        }
                        _rs.persist_error(wdog_connector, _rs.RESOURCE_TYPE_MODEL, model_id, 'watchdog_timeout', err_blob, blocking=True)
                        wdog_connector.close()
                except Exception:  # NOQA
                    pass

                in_message_['in_message'] = json.dumps(in_message_)
                in_message_['watchdog_restart'] = True
                in_message_['is_primary'] = is_primary

                out_queue.put(json.dumps(in_message_))
                exit_event.set()

    message_ = {'exit_loop': 1}
    out_queue.put(json.dumps(message_))


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

    def start(self, is_primary):
        """
        Start the model child process.

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
        self.out_queue.put(is_primary)

    def is_alive(self):
        return self.process.is_alive()

    def send(self, message):
        """Queue an image identifier for background resource collection.

        :param message: message to send.
        :type message: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        self.out_queue.put_nowait(message)
        self.sleep_event.set()

    def recv(self):  # NOQA
        if not self.in_queue.empty():
            message = self.in_queue.get_nowait()
            return json.loads(message)

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
            print('model process is stuck')
