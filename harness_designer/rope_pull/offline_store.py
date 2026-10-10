"""Per-chain working state for a peg-board drag.

While a peg-board drag runs, each chain it touches keeps an in-memory
overlay: the ordered waypoints the chain currently has in service. Entries
are either database-backed points (``point_id`` set) or in-memory points
created mid-drag (``point_id`` None, written to the database only when the
drag releases). Waypoints the solver no longer needs are taken out of the
overlay from the chain's anchor end (the end not being moved) and kept in
that chain's store, index 0 = most recently given up. They come back from
there first when the chain needs slack again.

Nothing else touches these structures during a drag, so they are purely
in-memory. The database is written once, when the drag releases (see
``handlers.rope_pull_handler``).
"""

_STORES: dict[bytes, list] = {}
_OVERLAYS: dict[bytes, list] = {}


def for_chain(chain_id: bytes) -> list:
    """The live store for *chain_id*, index 0 = most recently given up."""
    return _STORES.setdefault(chain_id, [])


def push(chain_id: bytes, entry: object) -> None:
    """Give up *entry* from *chain_id*, placing it at index 0 of the store."""
    for_chain(chain_id).insert(0, entry)


def pop_front(chain_id: bytes) -> object:
    """Take the most recently given-up entry of *chain_id* back."""
    return for_chain(chain_id).pop(0)


def overlay(chain_id: bytes) -> list | None:
    """The chain's live overlay (its in-service waypoints, in order), or
    ``None`` when no drag has touched the chain yet."""
    return _OVERLAYS.get(chain_id)


def set_overlay(chain_id: bytes, entries: list) -> None:
    """Start the drag overlay for *chain_id*."""
    _OVERLAYS[chain_id] = entries


def overlay_points(chain_id: bytes) -> list | None:
    """The overlay's live ``Point`` objects in order, for the strand to draw
    from, or ``None`` when no drag overlay is active for *chain_id*."""
    entries = _OVERLAYS.get(chain_id)
    if entries is None:
        return None

    return [entry.point for entry in entries]


def release(chain_id: bytes) -> list:
    """Empty *chain_id*'s store and return what it held."""
    return _STORES.pop(chain_id, [])


def release_overlay(chain_id: bytes) -> list | None:
    """End the drag overlay for *chain_id* and return its entries, or ``None``
    if there was none."""
    return _OVERLAYS.pop(chain_id, None)
