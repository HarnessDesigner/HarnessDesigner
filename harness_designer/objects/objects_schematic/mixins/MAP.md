## FILES

#### __init__.py

Empty package — `__init__.py` only, no definitions of any kind (confirmed via `dep_trace.py --name`). CODEBASE_MAP.md describes the (then-named) `objects2d/mixins/` as having `angle` and `move` mixin files, matching what it claims for `objects3d/mixins/`. Neither ever materialized here (nor does `objects_3d/mixins/` have them — see the drift note in `objects/MAP.md`). Schematic wire-type behavior also has no mixin override the way 3D (`objects_3d/mixins/wire_type.py`) and peg-board (`objects_pegboard/mixins.py`) do — `objects_schematic/wire.py` presumably implements whatever it needs directly rather than through a mixin. Confirm current behavior in `objects_schematic/wire.py` directly if working on schematic wire-picking logic; this directory is not where it lives.
