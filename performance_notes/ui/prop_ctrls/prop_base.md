# harness_designer/ui/prop_ctrls/prop_base.py

## `Property._send_changed_event` - allocates a new `PropertyEvent` per emission
Each change builds a fresh `PropertyEvent`, sets three fields and emits it. The allocation is a few attribute writes, so the cost is negligible compared with the Qt event dispatch. The slider-tick volume (see `float_prop.md`) is the real concern, not this allocation.

## `Property.SetToolTip` - no cost concern
Two setter calls per invocation. Called from the property grid on refresh, not per frame.
