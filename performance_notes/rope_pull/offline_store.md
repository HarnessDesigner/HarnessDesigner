# harness_designer/rope_pull/offline_store.py

Per-chain working state for a peg-board drag, held in two module-level dicts (`_STORES`, `_OVERLAYS`) keyed by chain id. Plain dict and list operations; O(1) per call except `overlay_points` (line 71), which loops over the overlay.

## Memory: entries live until released
Both dicts grow with every chain a drag touches and shrink only through `release` / `release_overlay` (lines 82 and 88). `handlers/rope_pull_handler.py` releases them in `_commit_points_body` (line 2614), `_commit_overlay` (3039) and `_on_stored_route_changed` (2801). A drag that is abandoned before any of those runs (a cancel path, an exception) would leave the chain's lists behind for the rest of the session (small per chain, but the dicts are process-wide). Check that the cancel path ends in one of them.
