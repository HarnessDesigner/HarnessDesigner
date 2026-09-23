# harness_designer/app_mixins/callback_mixin.py

This class is the callback backbone for `Point`/`Angle` (see MEMORY.md) --
`_process_callbacks` fires on every position/angle mutation across the
whole app, so it is about as hot a path as this codebase has.

## Line 144-173 (`_process_callbacks`) — several O(n) list-membership checks per call, needs investigation before changing
Three separate places do `x in some_list`/`some_list.remove(x)` against
plain lists while iterating the callback set:
- `if ref in used_callbacks: continue` inside the main firing loop.
- `elif cb in self.__unbound_callbacks__: self.__unbound_callbacks__.remove(cb)`
  in the pruning pass.
- The final rebuild's list comprehension re-checks
  `ref not in self.__callbacks__ and ref() not in self.__unbound_callbacks__`
  for every surviving callback.

Each is O(n) per check, so the whole method is roughly O(n^2) in the number
of bound callbacks on a single Point/Angle. In practice n (callbacks per
Point/Angle instance) is probably small, so this may not matter -- flagging
because of call frequency, not because n is known to be large.

A `set()` would make these membership checks O(1), but the method's own
comment block (lines 136-141) documents that `weakref.WeakMethod` equality
is content-based while the referent is alive (two distinct `WeakMethod`
wrapper objects can compare equal), which is exactly the kind of thing that
changes behavior under a `set` (hashing/dedup semantics) in a way that
isn't obviously safe without understanding why the list-based approach was
chosen. Needs a deeper look at `WeakMethod.__eq__`/`__hash__` interaction
with this method's dedup logic before changing the container type -- don't
convert to `set` without confirming the dedup behavior stays identical.
