# performance_notes/ui/prop_ctrls

Covers `harness_designer/ui/prop_ctrls/`.

- [_image_ctrl_base.md](_image_ctrl_base.md) - image and PDF loading on the UI thread (the main concern in this folder)
- [float_prop.md](float_prop.md) - slider and spin-box change events
- [_array_dialog_base.md](_array_dialog_base.md) - array dialog construction and focus handling
- [prop_base.md](prop_base.md) - base property event emission

## Reviewed for performance
The files above were read for the hot paths described. The remaining property controls (`angle_prop`, `point_prop`, `int_prop`, `color_prop`, `path_prop`, `model3d_prop`, `datasheet_cad_prop`, `tri_state_checkbox_prop`, and the rest) follow the same event-emit pattern as `float_prop.py` and were checked only for construction and event handling, not line by line. They have no notes of their own yet.
