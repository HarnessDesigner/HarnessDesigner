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
        selected_color = [0.2, 0.6, 0.2, 0.35]
        background_color = [1.0, 0.96, 0.96, 1.0]

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
            """Represent a floor in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

            UNKNOWN details are inferred from the class name and surrounding code.
            """
            enable = True
            ground_height = 0.0
            distance = 300
            enable_floor_lock = False

            class grid:
                """Represent a grid in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

                UNKNOWN details are inferred from the class name and surrounding code.
                """
                primary_color = [0.8, 0.1, 0.1, 0.3]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.3]
                size = 50
                enable = False

            class reflections:
                """Represent a reflections in :mod:`harness_designer.ui.dialogs.housing_editor.config`.

                UNKNOWN details are inferred from the class name and surrounding code.
                """
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
