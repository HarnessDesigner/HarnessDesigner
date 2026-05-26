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
    """Execute the ocp read shape operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param shape: Value for ``shape``.
    :type shape: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    BRepMesh_IncrementalMesh(
        theShape=shape, theLinDeflection=0.001,
        isRelative=True, theAngDeflection=0.1, isInParallel=True
        )

    vertices = []
    faces = []
    offset = 0

    anExpSF = TopExp_Explorer(shape, TopAbs_FACE)
    while anExpSF.More():
        if anExpSF.Current().ShapeType() != TopAbs_FACE:
            continue

        aLoc = TopLoc_Location()

        poly_triangulation = (
            BRep_Tool.Triangulation_s(
                TopoDS.Face_s(anExpSF.Current()),
                aLoc
                ))  # NOQA

        if not poly_triangulation:
            continue

        trsf = aLoc.Transformation()

        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            vertices.append(pnt)

        facet_reversed = anExpSF.Current().Orientation() == TopAbs_REVERSED

        order = [1, 3, 2] if facet_reversed else [1, 2, 3]
        for tri in poly_triangulation.Triangles():
            faces.append([tri.Value(i) + offset - 1 for i in order])

        offset += node_count
        anExpSF.Next()

    vertices = np.array(vertices, dtype=np.float64)
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

    vertices = np.array(vertices, dtype=np.float64).reshape(-1, 3)
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

    connector = db_broker.connect_to_database(credentials)

    if connector is None:
        with print_lock:
            print('MODEL DOWNLOADER: unknown database type')
        return

    from .. import resources as _resources

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

            in_message = in_queue.get_nowait()
            in_message = json.loads(in_message)

            model_id = in_message['id']
            mfg = in_message['mfg']
            part_number = in_message['part_number']
            model_dir = in_message['model_dir']

            message = {'step': 1, 'id': model_id, 'mfg': mfg, 'part_number': part_number}
            out_queue.put(json.dumps(message))

            if exit_event.is_set():
                break

            connector.execute(f'SELECT target_count, aggressiveness, update_rate, iterations, simplify, path FROM models3d WHERE id={model_id};')
            model_data = connector.fetchall()

            if not model_data:
                message = {'err': 'invalid database row',
                           'id': model_id,
                           'mfg': mfg, 'part_number': part_number}

                out_queue.put(json.dumps(message))
                continue

            if exit_event.is_set():
                break

            message['step'] = 2
            out_queue.put(json.dumps(message))

            target_count, aggressiveness, update_rate, iterations, simplify, path = model_data[0]

            if not path:
                message['err'] = 'invalid model url/path'
                out_queue.put(json.dumps(message))
                continue

            if exit_event.is_set():
                break

            message['step'] = 3
            out_queue.put(json.dumps(message))

            file_path = _resources.collect_resource(connector, _resources.IMAGE_TYPE_MODEL, path)

            if file_path is None:
                message['err'] = 'unable to load model'
                out_queue.put(json.dumps(message))
                continue

            if exit_event.is_set():
                break

            message['step'] = 4
            out_queue.put(json.dumps(message))

            ext = os.path.splitext(file_path)[-1]

            connector.execute(f'SELECT id, extension FROM file_types WHERE extension={ext[1:]};')
            file_type = connector.fetchall()
            if not file_type:
                message['err'] = f'unsupported file type ("{ext[1:]}")'
                out_queue.put(json.dumps(message))
                continue

            if exit_event.is_set():
                break

            file_type_id, ext = file_type[0]

            message['step'] = 5
            out_queue.put(json.dumps(message))

            try:
                vertices, faces = _load(file_path)
            except Exception:  # NOQA

                import traceback
                err = ''.join(traceback.format_exc())
                message['err'] = err

                out_queue.put(json.dumps(message))
                continue

            if exit_event.is_set():
                break

            vertices = _center_model(vertices)

            if simplify:
                message['step'] = 6
                out_queue.put(json.dumps(message))

                vertices, faces = _reduce_triangles(
                    vertices, faces, target_count, aggressiveness, iterations)

            message['step'] = 7
            out_queue.put(json.dumps(message))

            vertices, smooth_normals, face_normals, _ = (
                _utils.compute_normals(vertices, faces))

            if exit_event.is_set():
                break

            message['step'] = 8
            out_queue.put(json.dumps(message))

            model_data = _model_data.ModelData(
                vertices,
                face_normals=face_normals,
                smooth_normals=smooth_normals
            )

            uuid = model_data.uuid
            model_data.source_location = path
            model_data.source_type = ext
            model_data.part_number = part_number
            model_data.manufacturer = mfg

            if exit_event.is_set():
                break

            model_data.save(model_dir)

            message['step'] = 9
            out_queue.put(json.dumps(message))

            connector.execute(f'UPDATE model3d SET file_type_id={file_type_id}, uuid="{uuid}" WHERE id={model_id};')
            connector.commit()

            message['step'] = 10
            out_queue.put(json.dumps(message))

    message = {'exit_loop': 1}
    out_queue.put(json.dumps(message))

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
