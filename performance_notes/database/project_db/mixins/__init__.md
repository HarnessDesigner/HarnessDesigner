# harness_designer/database/project_db/mixins/__init__.py

Facade: imports every `pjt_*` column mixin (position, angle, scale, visible, name, notes, ...) and re-exports each name. No per-call cost; the work per property access is in the individual mixin notes. Importing the package loads all of them, so it only affects startup.
