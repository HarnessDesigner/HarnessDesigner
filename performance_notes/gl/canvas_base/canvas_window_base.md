# harness_designer/gl/canvas_base/canvas_window_base.py

## Line 46-84 (`CanvasWindowBase.__init__`) — construction only
Runs once per window. Nothing on the frame path.

**Functional bug (flagged, not fixed):** line 74 does `vw, vh = size`. `CanvasWindow` for the peg-board (`canvas_pegboard/canvas_window.py`) now accepts `size: tuple[int, int] | None = None` and forwards it unchanged. If the default is used, this line raises `TypeError: cannot unpack non-iterable NoneType`. Nothing catches it, because `_check_types.do` is a no-op decorator. Either the peg-board window needs a real default size, or the base needs to handle `None`.

## Line 120-143 (`resizeEvent`) — recentres the inner canvas on every resize
Each resize recomputes the offset and calls `move()`. Cheap. Calls `_try_fit_all` at the end, which returns early unless a fit was requested.

## Line 145-159 (`showEvent`) — deferred fit
Schedules `_try_fit_all` on the next event-loop turn. One timer per show. Fine.

## Line 205-295 (`_camera_state`, `_padded_bounds`, `_apply_fit`, `_try_fit_all`) — fit logic
Runs on resize and show while a fit is pending. Once the user pans or zooms, the request is dropped, so it stops running. Each run is a few NumPy operations. Fine.

## Line 351-398 (`objects_in_window`) — linear scan with one projection per object
Walks every visible object in the AABB pool and calls `camera.ProjectPoint` on each. The cost is linear in the number of visible objects. It is used only for the "re-centre on selection" decision (per the docstring), so it is not per frame. Fine at current scale.

**Typing:** `-> list` (bare) changed to `-> list["_objects.ObjectBase"]` in this pass. The elements are `view_obj.parent`, the object facade.

## Line 400-443 (`required_zoom_scale`) — eight projections per call
Projects the eight AABB corners. Called on demand when centring on an object. Fine.

## Line 445-605 (forwarders and property wrappers)
Mostly one-line forwards to `self._canvas`. Each adds one Python call; not on a measured hot path. Note `Refresh` returns early while `_ref_count` is non-zero, which is how batching works.
