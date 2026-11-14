# harness_designer/drag_handlers/editor_schematic/__init__.py

Holds `DragHandlerSchematic`, the shared base for the schematic drag handlers. Its only logic is `_world_xz` (line 40), one `camera.screen_to_world` call per mouse move. Cheap. The schematic drags are never length-budget clamped, so the base adds nothing else to the move path.
