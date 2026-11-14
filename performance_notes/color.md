# harness_designer/color.py

## Line 25-35 (`ColorMeta._remove_ref`) — linear scan of the whole color cache for each dead color
Every cached db-backed `Color` is registered with `weakref.ref(instance, cls._remove_ref)` (lines 62-64 and 72-74). The one shared callback does not know which key died, so it takes the RLock, copies `list(cls._instances.items())` and compares `value == ref` entry by entry. Cost is O(n) in the number of live db-backed colors, plus a list copy of that size, every time a color is garbage collected.
Fix: bind the key when the weakref is made (`weakref.ref(instance, functools.partial(cls._remove_ref, db_id))`), then delete `cls._instances[db_id]` directly (guarding against a newer entry having replaced it). One small `partial` object per cached color is the memory price; it is negligible next to the `Color` itself. Only worth doing if the db-color count gets into the thousands or colors churn while editing, which a real project with many catalog parts can reach. Measure the cache size in a large project first.

## Line 38-80 (`ColorMeta.__call__`) — cached path does two dict lookups and one weakref deref
For db-backed colors it takes the RLock, checks `db_id in _instances`, derefs once to test liveness and derefs again to return. Acceptable. Colors without `db_id` skip the cache and construct normally.

## Line 384-455 (`from_int`, `GetLighterColor`, `GetDarkerColor`, `from_qcolor`)
Each builds one new `Color` (and with it the `CallbackMixin` bookkeeping). These are called from UI/theme code, not per frame. Fine.
