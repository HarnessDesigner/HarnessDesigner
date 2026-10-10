# harness_designer/gl/canvas_3d/headlight.py

## Line 36-37 (`Headlight.__init__`) — subscribes to camera position and focal point
Binds `__update` to two observable points, so the direction recomputes whenever the camera moves or its focal point moves. During a drag, that can be many times per frame.

## Line 39-47 (`Headlight.__update`) — recomputes direction on every camera move
Builds `direction` from `Point` subtraction, then a `sum` over `d ** 2` and a list comprehension. That is several small allocations per call. It could be done once per frame in `set` rather than on every callback, but the callbacks are cheap enough that this is minor.

**Possible bug:** `magnitude` is zero when the camera position equals the focal point. Line 47 then divides by zero and raises `ZeroDivisionError` inside the observer callback. Not verified by running. Needs a guard if the two points can coincide.

## Line 49-63 (`Headlight.set`) — per-frame uniform writes and two small NumPy arrays
Each frame it writes five uniforms. `np.array(self.config.color, dtype=np.float32)` is built every frame; it could be built once when the config changes. `math.radians(self.config.cutoff)` is also recomputed per frame.
