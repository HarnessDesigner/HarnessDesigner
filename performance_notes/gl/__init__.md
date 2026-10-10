# harness_designer/gl/__init__.py

## Whole file — import-time re-exports only
The module binds about 60 `EVT_GL_*` constants and five event classes from `events`, then `del _events`. Everything happens once at import, so there is no runtime cost. The only thing to watch is that these names are a flat re-export of `events`; adding a new event means touching both files.
