# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .... import config as _config


class Config:

    class editor3d:
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
            enable = False
            cutoff = 8.0
            dissipate = 50.0
            color = [0.6, 0.6, 0.4, 0.8]

        class virtual_canvas:
            width = 1920
            height = 1080

        class floor:
            enable = True
            ground_height = 0.0
            distance = 300
            enable_floor_lock = False

            class grid:
                primary_color = [0.8, 0.1, 0.1, 0.3]
                secondary_color = [0.2925, 0.3430, 0.3430, 0.3]
                size = 50
                enable = False

            class reflections:
                enable = False
                strength = 50.0

        class renderer:
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
            enable = False
            color = [1.0, 0.4, 0.4, 1.0]
            radius = 0.25

        class axis_overlay:
            is_visible = False
            size = (35, 35)
            position = (0, 0)
