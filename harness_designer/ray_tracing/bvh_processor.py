
# threaded_bvh_processor.py
import threading
import queue
import time
import numpy as np
import bvh_fast
from dataclasses import dataclass
from typing import Optional, List, Tuple

@dataclass
class ObjectData:
    """Data for a single object to process"""
    object_id: int
    vertices: np.ndarray      # (N, 3) float32
    faces: np.ndarray         # (M, 3) int32
    normals: np.ndarray       # (M, 3) float32
    position: np.ndarray      # (3,) float32
    rotation: np.ndarray      # (3, 3) float32 or (4,) quaternion
    material_id: int

@dataclass
class ProcessedObject:
    """Results from processing an object"""
    object_id: int
    vertices: np.ndarray      # Transformed vertices
    faces: np.ndarray         # Original faces
    normals: np.ndarray       # Transformed normals
    bvh_bounds: np.ndarray    # BVH bounds
    bvh_structure: np.ndarray # BVH structure
    bvh_indices: np.ndarray   # BVH indices
    material_id: int
    processing_time: float    # ms

class BVHWorkerThread(threading.Thread):
    """Worker thread that processes objects from queue"""

    def __init__(self, thread_id: int, work_queue: queue.Queue,
                 results_queue: queue.Queue, stats_lock: threading.Lock):
        super().__init__(daemon=True)
        self.thread_id = thread_id
        self.work_queue = work_queue
        self.results_queue = results_queue
        self.stats_lock = stats_lock
        self.objects_processed = 0
        self.total_time = 0.0
        self.running = True

    def run(self):
        """Main thread loop"""
        print(f"[Thread {self.thread_id}] Started")

        while self.running:
            try:
                # Get work from queue (blocks until available)
                obj_data = self.work_queue.get(timeout=0.1)

                # Check for poison pill (shutdown signal)
                if obj_data is None:
                    print(f"[Thread {self.thread_id}] Received shutdown signal")
                    break

                # Process the object
                start_time = time.time()
                result = self._process_object(obj_data)
                elapsed = (time.time() - start_time) * 1000

                result.processing_time = elapsed

                # Put result in results queue
                self.results_queue.put(result)

                # Update stats
                with self.stats_lock:
                    self.objects_processed += 1
                    self.total_time += elapsed

                # Mark task as done
                self.work_queue.task_done()

            except queue.Empty:
                # No work available, loop continues
                continue
            except Exception as e:
                print(f"[Thread {self.thread_id}] Error processing object: {e}")
                import traceback
                traceback.print_exc()
                self.work_queue.task_done()

        print(f"[Thread {self.thread_id}] Exiting "
              f"(processed {self.objects_processed} objects, "
              f"avg {self.total_time / max(1, self.objects_processed):.1f}ms/object)")

    def _process_object(self, obj_data: ObjectData) -> ProcessedObject:
        """Process a single object: transform + BVH build"""

        # 1. Apply transforms (if not identity)
        if not (np.allclose(obj_data.position, 0) and
                np.allclose(obj_data.rotation, np.eye(3))):

            # Handle quaternion if needed
            if obj_data.rotation.shape == (4,):
                rotation_mat = bvh_fast.quaternion_to_rotation_matrix(obj_data.rotation)
            else:
                rotation_mat = obj_data.rotation

            # Transform vertices and normals
            transformed_verts, transformed_normals = bvh_fast.apply_transform_parallel(
                obj_data.vertices,
                obj_data.normals,
                obj_data.position,
                rotation_mat
            )
        else:
            # No transform needed (identity)
            transformed_verts = obj_data.vertices
            transformed_normals = obj_data.normals

        # 2. Calculate centroids
        centroids = bvh_fast.calculate_centroids_parallel(
            transformed_verts,
            obj_data.faces
        )

        # 3. Build BVH
        bvh_builder = bvh_fast.FastBVHBuilder(
            transformed_verts,
            obj_data.faces,
            centroids,
            leaf_threshold=4
        )
        bvh_bounds, bvh_structure, bvh_indices = bvh_builder.build()

        # 4. Return processed result
        return ProcessedObject(
            object_id=obj_data.object_id,
            vertices=transformed_verts,
            faces=obj_data.faces,
            normals=transformed_normals,
            bvh_bounds=bvh_bounds,
            bvh_structure=bvh_structure,
            bvh_indices=bvh_indices,
            material_id=obj_data.material_id,
            processing_time=0.0  # Will be set by caller
        )


class ThreadedBVHProcessor:
    """Manages worker threads for parallel BVH processing"""

    def __init__(self, num_threads: int = 10):
        self.num_threads = num_threads
        self.work_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.stats_lock = threading.Lock()
        self.threads: List[BVHWorkerThread] = []
        self.running = False

        print(f"ThreadedBVHProcessor: {num_threads} threads")

    def start(self):
        """Start worker threads"""
        if self.running:
            print("Warning: Threads already running")
            return

        print(f"Starting {self.num_threads} worker threads...")
        start_time = time.time()

        self.threads = []
        for i in range(self.num_threads):
            thread = BVHWorkerThread(
                thread_id=i,
                work_queue=self.work_queue,
                results_queue=self.results_queue,
                stats_lock=self.stats_lock
            )
            thread.start()
            self.threads.append(thread)

        self.running = True
        elapsed = (time.time() - start_time) * 1000
        print(f"Threads started in {elapsed:.1f}ms")

    def process_objects(self, objects: List[ObjectData]) -> List[ProcessedObject]:
        """
        Process multiple objects in parallel

        Args:
            objects: List of ObjectData to process

        Returns:
            List of ProcessedObject results (order preserved)
        """
        if not self.running:
            raise RuntimeError("Threads not started! Call start() first.")

        num_objects = len(objects)
        print(f"\nProcessing {num_objects} objects across {self.num_threads} threads...")

        start_time = time.time()

        # 1. Submit all work to queue
        for obj in objects:
            self.work_queue.put(obj)

        print(f"  ✓ Submitted {num_objects} objects to queue")

        # 2. Wait for all work to complete
        self.work_queue.join()

        # 3. Collect results
        results = []
        while not self.results_queue.empty():
            results.append(self.results_queue.get())

        # 4. Sort results by object_id to preserve order
        results.sort(key=lambda x: x.object_id)

        total_time = (time.time() - start_time) * 1000

        # Print statistics
        total_processing_time = sum(r.processing_time for r in results)
        avg_per_object = total_processing_time / num_objects
        speedup = total_processing_time / total_time

        print(f"  ✓ Completed in {total_time:.1f}ms")
        print(f"    - Total processing time: {total_processing_time:.1f}ms")
        print(f"    - Avg per object: {avg_per_object:.1f}ms")
        print(f"    - Parallel speedup: {speedup:.1f}x")
        print(f"    - Efficiency: {(speedup / self.num_threads) * 100:.1f}%")

        return results

    def shutdown(self):
        """Gracefully shutdown all worker threads"""
        if not self.running:
            return

        print("\nShutting down worker threads...")
        start_time = time.time()

        # Send poison pill to each thread
        for _ in range(self.num_threads):
            self.work_queue.put(None)

        # Wait for all threads to finish
        for thread in self.threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                print(f"Warning: Thread {thread.thread_id} did not exit cleanly")

        self.running = False
        self.threads = []

        elapsed = (time.time() - start_time) * 1000
        print(f"Threads shut down in {elapsed:.1f}ms")

    def __enter__(self):
        """Context manager support"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.shutdown()
