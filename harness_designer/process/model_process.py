# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import multiprocessing
import os
import time
import threading
import numpy as np
import queue
import pyfqmr
import traceback
import uuid as _uuid
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
from .. import resources as _resources

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
            TopoDS.Face_s(anExpSF.Current()), aLoc)  # NOQA

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


class ThreadWorker(threading.Thread):

    def __init__(self, db_broker, credentials, message, out_queue):
        self.db_broker = db_broker
        self.credentials = credentials
        self.message = message
        self.out_queue = out_queue

        threading.Thread.__init__(self)
        self.daemon = True
        self.result = None
        self.exception = None

    def run(self):
        connector = None

        try:
            connector = self.db_broker.connect_to_database(self.credentials)
            if connector is None:
                raise RuntimeError('database connection error')

            message = self.message

            model_id = message['id']
            model_dir = message['path']

            message['step'] = 1

            self.out_queue.put(message)

            connector.execute(f'SELECT target_count, aggressiveness, '
                              f'update_rate, iterations, simplify, '
                              f'path FROM models3d WHERE id={model_id};')

            model_data = connector.fetchall()

            if not model_data:
                message['err_msg'] = 'invalid database row'
                message['err_no'] = -10001
                message['allow_retry'] = False,

                self.out_queue.put(message)
                connector.close()
                return

            message['step'] = 2
            self.out_queue.put(message)

            (target_count, aggressiveness, update_rate,
             iterations, simplify, path) = model_data[0]

            if not path:
                message['err_msg'] = 'invalid model url/path'
                message['err_no'] = -10002
                message['allow_retry'] = True

                self.out_queue.put(message)
                connector.close()
                return

            message['step'] = 3
            self.out_queue.put(message)

            try:
                file_path = _resources.collect_resource(
                    connector, _resources.RESOURCE_TYPE_MODEL, path)
            except _resources.RequestsError as err:
                message['err_no'] = err.code
                message['err_msg'] = err.__msg__
                tb = traceback.format_exception(err)
                message['traceback'] = ''.join(tb)
                message['allow_retry'] = True
                self.out_queue.put(message)
                connector.close()

                return
            # catchall for all other resource exceptions
            except _resources.ResourceException as err:
                message['err_no'] = err.code  # NOQA
                message['err_msg'] = err.__msg__
                message['err_path'] = err.path  # NOQA
                tb = traceback.format_exception(err)
                message['traceback'] = ''.join(tb)
                message['allow_retry'] = False
                self.out_queue.put(message)
                connector.close()

                return
            except Exception as err:
                tb = traceback.format_exception(err)
                message['traceback'] = ''.join(tb)
                message['allow_retry'] = False
                self.out_queue.put(message)
                self.out_queue.put(message)
                connector.close()

                return

            if file_path is None:
                message['err_no'] = -10003
                message['err_msg'] = f'This should not occur "models3d" ({model_id})'
                message['allow_retry'] = False
                self.out_queue.put(message)
                self.out_queue.put(message)
                connector.close()

                return

            message['step'] = 4
            self.out_queue.put(message)

            model_path, file_type_id = file_path

            connector.execute(
                f'SELECT extension FROM file_types WHERE id={file_type_id};')

            rows = connector.fetchall()

            if not rows:
                message['err_msg'] = 'unsupported file type'
                message['err_no'] = -10004
                message['allow_retry'] = False
                self.out_queue.put(message)
                connector.close()
                return

            ext = rows[0][0]

            message['step'] = 5
            self.out_queue.put(message)

            if not os.path.exists(model_path):
                message['err_msg'] = f'file does not exist ("{model_path}")'
                message['err_no'] = -10005
                message['allow_retry'] = False

                self.out_queue.put(message)
                connector.close()
                return

            vertices, faces = _load(model_path)

            vertices = _center_model(vertices)

            if simplify:
                message['step'] = 6
                self.out_queue.put(message)

                vertices, faces = _reduce_triangles(
                    vertices, faces, target_count, aggressiveness, iterations
                )

            message['step'] = 7
            self.out_queue.put(message)

            packed, vertex_count = _utils.compute_normals(vertices, faces)

            message['step'] = 8
            self.out_queue.put(message)

            # The packed array is saved as a plain uncompressed .npy file.
            # The parent opens the file as a numpy memory map and streams
            # it straight into the GPU vertex buffer.
            unpacked_verts = packed[:vertex_count * 3].reshape(-1, 3)
            aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
            aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
            aabb = [[float(str(item2)) for item2 in item1] for item1 in aabb.tolist()]
            obb = _utils.compute_obb(aabb1,  aabb2)
            obb = [[float(str(item2)) for item2 in item1] for item1 in obb.tolist()]

            uuid = str(_uuid.uuid4())

            directory = os.path.join(model_dir, uuid[:2])
            os.makedirs(directory, exist_ok=True)

            np.save(os.path.join(directory, f'{uuid}.npy'), packed)

            message['step'] = 9
            self.out_queue.put(message)

            # Only DB writes permitted from child: uuid, file_type_id and
            # the model metadata (vertex_count, aabb, obb).
            connector.execute(f'UPDATE models3d SET file_type_id={file_type_id}, '
                              f'uuid="{uuid}", '
                              f'vertex_count={vertex_count}, '
                              f"aabb='{str(aabb)}', "
                              f"obb='{str(obb)}' "
                              f'WHERE id={model_id};')

            connector.commit()

            message['step'] = 10
            self.out_queue.put(message)

            os.remove(model_path)

            # Step 10: final success; parent updates resource_state.
            message['step'] = 11
            self.out_queue.put(message)

            connector.close()
        except Exception as err:  # NOQA
            self.exception = err
            if connector is not None:
                connector.close()


def _process_worker(in_queue: multiprocessing.Queue, out_queue: multiprocessing.Queue,
                    exit_event: multiprocessing.Event, print_lock: multiprocessing.Lock):

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
        out_queue.put({'log': 'MODEL DOWNLOADER: error collecting credentials'})
        return

    from . import db_broker
    from .. import config as _config

    while not exit_event.is_set():
        if is_primary:
            message = in_queue.get()
        else:
            try:
                message = in_queue.get(120)
            except queue.Empty:
                break

        if message is None:
            continue

        timeout = _config.Config.resources.model_watchdog_timeout

        thread = ThreadWorker(db_broker, credentials, message, out_queue)
        start_time = time.time()

        thread.start()

        stop_time = time.time()
        while stop_time - start_time <= timeout:
            if thread.is_alive():
                exit_event.wait(0.1)
            else:
                break

            stop_time = time.time()

        if thread.exception is not None:
            # Unhandled exception: pass error info to parent for DB update.
            message['err_no'] = -10000
            message['err_msg'] = 'Unknown Error'
            message['allow_retry'] = False
            tb = traceback.format_exception(thread.exception)
            message['tb'] = ''.join(tb)

            out_queue.put(message)
            continue

        if stop_time - start_time > timeout:
            # Watchdog timeout: parent will persist as a blocking issue.
            message['watchdog_restart'] = True
            message['is_primary'] = is_primary
            message['err_msg'] = 'watchdog timeout'
            message['err_no'] = -10100
            message['allow_retry'] = False
            out_queue.put(message)
            exit_event.set()

    message = {'exit_loop': 1}
    out_queue.put(message)


class ProcessWorker:

    def __init__(self, manager: "_manager.ProcessManager",
                 print_lock: multiprocessing.Lock):

        self.manager = manager
        self.exit_event = multiprocessing.Event()
        self.in_queue = multiprocessing.Queue()
        self.out_queue = multiprocessing.Queue()

        self.process = multiprocessing.Process(
            target=_process_worker,
            args=(self.out_queue, self.in_queue, self.exit_event, print_lock))

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
        self.out_queue.put(message)

    def recv(self):  # NOQA
        if not self.in_queue.empty():
            message = self.in_queue.get_nowait()
            return message

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

        from .. import config as _config

        self.process.join(_config.Config.resources.model_watchdog_timeout + 3.0)
        if self.process.is_alive():
            print('model process is stuck')
