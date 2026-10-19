# Plugin framework design

`harness_designer/plugins/` is the registration mechanism every kind of plugin (AI, and later
database/scraper/3D/schematic/pegboard plugins) is built on. This file explains what the classes
here do. Decisions about a specific *kind* of plugin belong in that kind's own subfolder (e.g.
`plugins/ai/AI_PLUGIN_DESIGN.md`), not here — this file is only the shared registration mechanism.

Status (2026-10-18): minimal, as the user intends it to stay at this layer — `plugin.py` and
`register.py` are ~30 lines each and do nothing but registration bookkeeping. There is no plugin
discovery/loading mechanism yet (no directory scan, no manifest, no enable/disable list); that is
future work once at least one real plugin (the AI ones) exists to design it against.

## Files

- `register.py` — `RegisterPlugin`: the metadata every plugin declares about itself (`name`,
  `plugin_type`, `short_description`, `description`, `author`, `email`, `support_url`, `icon`).
  Plain data holder, no behavior.
  - `PLUGIN_TYPE_*` — a bitmask (not a plain enum) because a plugin can legitimately belong to
    more than one category at once. Currently: `MISC`, `DATABASE`, `SCRAPER`, `3D`, `SCHEMATIC`,
    `PEGBOARD`, and `AI` (added for `plugins/ai/`, see that folder's design doc).
- `plugin.py` — `Plugin`, the base every concrete plugin subclasses, plus the registration
  mechanism that attaches a `RegisterPlugin` instance to a `Plugin` subclass:
  - `start_registration(instance)` sets a module-level "currently registering" slot. Call it with
    a `RegisterPlugin(...)` immediately before the `class Foo(Plugin):` statement that it
    describes.
  - `_PluginMeta` (the metaclass behind `Plugin`) reads that slot at class-creation time and
    stores it as `cls._registration`. This is why the `start_registration(...)` call and the
    `class` statement it belongs to must be adjacent — there is currently no guard preventing a
    second class statement from picking up a registration meant for a different one, and nothing
    resets the slot back to `None` after it's consumed. Future plugin kinds should keep that
    ordering strict until/unless this gets hardened (e.g. a decorator that does both steps
    atomically) — not changed here without checking first, since the AI plugin work builds on
    the mechanism as it exists today rather than changing it.

## Using it

```python
from harness_designer.plugins import plugin as _plugin
from harness_designer.plugins import register as _register

_plugin.start_registration(_register.RegisterPlugin(
    name='Example',
    plugin_type=_register.PLUGIN_TYPE_MISC,
    short_description='...',
    description='...',
    author='...',
    email='...',
    support_url='...',
))


class ExamplePlugin(_plugin.Plugin):
    ...
```

## What is not built yet

- Discovery: nothing currently finds/imports plugin modules — a concrete plugin class existing in
  the tree does not mean the app loads it.
- Enable/disable, and anywhere a user picks which plugin is "active" for a given purpose (e.g.
  which AI plugin to use) — this is being designed alongside the AI plugin work and the settings
  UI (in progress separately); it will likely live here once more than one plugin kind needs it.
- A settings-panel base class every plugin subclasses to contribute its own settings page (widget
  factory helpers + scoped access to the app's config database) — in progress separately from
  this file; record its design here once built.
