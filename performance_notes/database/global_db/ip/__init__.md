# harness_designer/database/global_db/ip/__init__.py

This file is not a facade: it holds `IPRatingsTable` and `IPRating`, the combined IP rating built from a solid, a fluid and an optional supplementary entry.

## Line 121-403 (`IPRating` properties) — cached after the first read
`name`, `ip_solid_id`, `ip_fluid_id`, `ip_supp_id`, `ip_solid`, `ip_fluid`, `ip_supp` and `pixmap` all use the `DefaultStoredValue` guard, so each issues its SQL once per row object. Row objects are per-id singletons (`IPRating in ...` check in `__getitem__`, line 87), so the cache is shared by every user of that rating.

## Line 353-381 (`short_desc`, `description`) — string rebuilt on every read
Both build a new f-string from the three cached parts each time they are read. The text is short and these are read when a tooltip or a property panel is built, not per frame. Not worth caching (the cached copy would cost more memory than the work it saves).

## Line 387-403 (`pixmap`) — one composited QPixmap per rating, kept for the row's lifetime
`ip_solid.icon | ip_fluid.icon` composites two icons and the result is cached in `_stored_pixmap`. That is the right trade: a QPixmap of icon size costs a few KB and the composite is not cheap. The memory is held as long as the `IPRating` wrapper is alive (it is a weak singleton), so unused ratings free their pixmap.

## Line 64-73 (`IPRatingsTable.__iter__`)
Yields one wrapper per row from the base iterator (one query for ids). Fine; the table is small (tens of rows).

## Line 76-98 (`__getitem__`)
Has the singleton short-circuit before the existence query for int/bytes keys; a name lookup always queries (`select('id', name=item)`), one round trip per call. Callers that look up by name in a loop should resolve once and keep the object.
