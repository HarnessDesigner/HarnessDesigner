# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .... import config as _config


class Config:
    """Represent a config in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    class editor3d:
        """Represent an editor 3D in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

        UNKNOWN details are inferred from the class name and surrounding code.
        """
        lighting = _config.Config.editor3d.lighting
        keyboard_settings = _config.Config.editor3d.keyboard_settings
        rotate = _config.Config.editor3d.rotate
        pan_tilt = _config.Config.editor3d.pan_tilt
        truck_pedestal = _config.Config.editor3d.truck_pedestal
        walk = _config.Config.editor3d.walk
        zoom = _config.Config.editor3d.zoom
        reset = _config.Config.editor3d.reset
        selected_color = _config.Config.editor3d.selected_color
        background_color = _config.Config.editor3d.background_color

        class headlight:
            """Represent a headlight in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            enable = False
            cutoff = 8.0
            dissipate = 50.0
            color = [0.6, 0.6, 0.4, 0.8]

        class virtual_canvas:
            """Represent a virtual canvas in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            width = 1920
            height = 1080

        class floor:
            """Floor plane, grid, and reflection settings for the 3D editor."""
            enable = True
            ground_height = 0.0
            size = 2000
            enable_floor_lock = False

            class grid:
                """Floor grid appearance settings."""
                primary_color = [0.2039, 0.2549, 0.2902, 0.0]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.0]

                primary_line_color = [0.87, 0.88, 0.92, 0.0]
                secondary_line_color = [0.57, 0.59, 0.65, 0.0]
                primary_line_width = 0.8
                secondary_line_width = 0.25

                secondary_lines_per_tile = 4

                secondary_line_pattern = 0x0B2664D0
                # 0000 1011 0010 0110 0110 0100 1101 0000
                secondary_line_shift = False

                size = 80
                enable = False

            class reflections:
                """Floor reflection settings in the 3D editor."""
                enable = False
                strength = 50.0

        class renderer:
            """Represent a renderer in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            smooth_covers = False
            smooth_boots = True
            smooth_housings = False
            smooth_wires = True
            smooth_bundles = True
            smooth_seals = True
            smooth_cpa_locks = False
            smooth_tpa_locks = False
            smooth_terminals = False

        class focal_target:
            """Represent a focal target in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            enable = False
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class axis_overlay:
            """Represent an axis overlay in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            is_visible = False
            size = (35, 35)
            position = (0, 0)
