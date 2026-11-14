# harness_designer/ui/dialogs/render_setings.py

RenderSettingsPanel (the controls: resolution, background, effects, ambient occlusion, lighting; apply() writes Config.ray_trace; a "Samples per pixel" spin box (samples, 1 to 1024) under the resolution; the Lighting group has a "Light at Camera" checkbox, lighting.camera_light; the Background group a "Match Viewport (background and floor)" checkbox, match_viewport), RenderSettingsDialog (a thin BaseDialog around the panel), LightingPanel (a QTabWidget, one tab per light labelled Light 1..Light n, with Add Light / Remove Light buttons; removing renumbers the remaining tabs) and LightItem (a tab's page: FloatCtrl spin+slider for X, Y and Z stacked vertically, then intensity with the colour button beside it).

Cold path (394 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
