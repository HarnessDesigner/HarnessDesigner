# harness_designer/ui/prop_ctrls/float_prop.py

## `FloatProperty._on_slider_scroll` - emits a change event for every slider tick
The slider's `valueChanged` fires on every tick while dragging, and each tick builds a `PropertyEvent` and emits `propertyChanged`. Nothing coalesces the events, and the handler does not check whether the rounded value actually changed. A drag across the slider can therefore emit hundreds of events, and each one flows to whoever is listening (the property grid, and any model refresh behind it). Emitting on slider release, or only when the snapped value differs from the last one emitted, would cut the event count to the number of distinct values.

## `FloatProperty._on_spin_changed` - no equality check before emitting
The spin box emits `valueChanged` on each keystroke or arrow step. The handler emits unconditionally, including when `setValue` on the slider was a no-op. A check against `self._value` before emitting would skip repeated identical events.

## `_d(self._inc)` - decimal conversion on every slider tick
`_on_slider_scroll` converts the increment through `_d(...)` each time. The increment is fixed for the control, so this could be computed once in `__init__`. The cost is small.
