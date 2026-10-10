# harness_designer/add_handlers/base.py

## `click_at` - replays a move and a click
Runs twice per right-click placement (one MOVE, one LEFT_UP). Negligible.

## `AddHandlerBase.__call__` - abstract
Subclasses override it. Nothing in the base class runs per move. No change.
