# harness_designer/ray_tracing/renderer.py

OpenCL renderer: builds the scene arrays, uploads them once, then runs the kernel over bands of rows, one pass per sample. Rewritten 2026-11-13 for the current design (one BVH for the scene, `kernel.cl`, memory-driven band size). It is an offline render, not an interactive path, so the questions are total time and memory, not per-frame cost.

## Line 205-238 (`_chunk_rows`) — band height from free memory, one buffer and a pixel cap
`rows = min(height, by_memory, by_buffer, by_pixels)` where `by_memory` is 80% of free memory (`MEMORY_FRACTION`) minus the scene bytes, `by_buffer` is the device's largest single allocation, and `by_pixels` caps a band at 1,000,000 pixels (`MAX_PIXELS_PER_CHUNK`). That is a sound way to trade memory for launches: fewer, larger bands mean fewer kernel launches but more device memory (12 bytes per pixel of the band). A band holds `rows x width x 12` bytes (at most 12 MB). Nothing to change; the 1,000,000-pixel cap is the knob if a GPU would run faster with bigger bands, and that needs a measurement on the real GPU.

## Line 275-419 (`_render`) — upload once, then per band and per pass
All scene arrays are uploaded once (`upload`, `COPY_HOST_PTR`), then for every band and every sample pass the kernel arguments are set again (about 50 `np.float32` / `np.int32` scalars, microseconds), the kernel is enqueued and `queue.finish()` waits for it. The waiting is per pass, which keeps cancel responsive (`self._cancel` is checked before each pass) at the cost of the CPU not preparing the next pass while the GPU runs; the preparation is microseconds, so this is the right trade. The preview copy back (`enqueue_copy` and a float -> uint8 conversion) is throttled to every 0.15 s (`PREVIEW_INTERVAL`) or the last pass of a band, so the readback does not dominate.
`rgb = (chunk_image[:chunk_height] * 255).astype(np.uint8)` converts a band on the CPU each time it is previewed; fine at preview rates.

## Line 90-124 (`init_cl`), 127-175 (`_detect_gpu`), 178-202 (`_free_memory`)
One-time setup. Compiling the kernel (`compile_kernel`) is the start-up cost; the compiled program is reused for all bands.

## Memory
The scene is held three times at peak: the Python lists, the concatenated NumPy arrays from `Scene.build` and the device buffers (see `scene.md`). The host copies can be released after the upload (the `data` object goes out of scope when `_render` returns, but it is alive during the whole render); dropping `data` references right after the uploads would free the host copy for the duration of a long render.
