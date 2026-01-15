import numpy as np
import pyfqmr


# TODO: Allow user to adjust the aggressiveness so they can evaluate the appearance.
#       This will allow them to optimize to get the best possible performance
#       from the application.

def reduce(verts: np.ndarray, faces: np.ndarray, target_count: int, 
           aggressiveness: float = 3.5, update_rate: int = 1,
           max_iterations: int = 150, lossless: bool = False,
           threshold_lossless: float = 1e-3, alpha: float = 1e-9, 
           K: int = 3) -> tuple[np.ndarray, np.ndarray]:
    
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
        target_count=target_count, update_rate=update_rate, max_iterations=max_iterations,
        aggressiveness=aggressiveness, lossless=lossless, threshold_lossless=threshold_lossless,
        alpha=alpha, K=K, verbose=False)

    vertices, faces, _ = mesh_simplifier.getMesh()
    
    return vertices, faces
