# harness_designer/add_handlers/editor_3d/housing.py

## `_follow` - per move
One focal-plane projection and one position update. Cheap. No change.

## `__call__` LEFT_UP - once per placement
`update_cavities` and `match_cavity_surfaces` run once. The comment in the code explains why they must run in this order. Not a concern.
