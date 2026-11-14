# harness_designer/shapes/twisted_path.pyx

The compiled path builder behind `TubeMixin._twist_segments` (`build_path`). One call turns a wire's straight segments into the pieces that are drawn (position, quaternion, matrix, length, twist phase, mitres, ring count), rounding the corners. Compiled with `boundscheck=False`, `wraparound=False`, `cdivision=True`, `nonecheck=False`; the helpers (`_frame`, `_transport_delta`, `_ring_count`) are `nogil` C functions on raw doubles.

## Cost and why it is built this way
The module docstring records the reason it exists: the Python path built a `Point` and an `Angle` through the Decimal-backed geometry classes for every chord, about 70 percent of the rebuild. This is the same finding as `geometry/decimal.md`, solved here by not using those classes at all. `build_path` itself is cheap; what remains in `_twist_segments` around it is the Python plan construction described in `objects/mixins/tube.md` (seven `.tolist()` calls and a `TwistSegment` per piece), which now costs more than the compiled call. Do that part lazily.

## Memory
Inputs and outputs are NumPy arrays sized by the piece count; nothing is retained here.
