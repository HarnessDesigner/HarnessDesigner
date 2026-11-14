# harness_designer/app_mixins/callback_mixin.py

This is the reactive backbone for `Point`, `Angle` and `Color` (see MEMORY.md). `_process_callbacks` runs on every mutation of a Point or Angle that is not inside a `with` batch, so it is among the hottest paths in the app. Anything saved here is saved on every drag frame.

Measured 2026-11-13 (interpreted Python 3.11, real `Point`): `_process_callbacks` costs 0.58 us with no listeners and 4.96 us with three listeners (whose own bodies are included); `p.x = 2.0` costs 0.79 us with none and 5.2 us with three. The callback system is cheap; the arithmetic that triggers it (`geometry/decimal.md`) is the expensive part of a move.

## Line 131-185 (`_process_callbacks`) — three small lists allocated per call, even with no callbacks
Each call does `del self.__unbound_callbacks__[:]`, builds `used_callbacks = []` and a copy `callbacks = self.__callbacks__[:]`, clears the callback list, loops, then rebuilds with a list comprehension. A Point with no bound callback (most vertices of a mesh path, many intermediate points) still pays the allocations and the clear/extend round trip.
Fix: an early exit for the empty case. It must still clear `__unbound_callbacks__`, because `unbind` (line 100) appends the strong bound-method reference of a callback it did not find there; leaving it would keep the callback's owner alive on a point that never fires again. So:
`if not self.__callbacks__: del self.__unbound_callbacks__[:]; return`.
No memory cost. The saving is only about 0.4 us per mutation of a listener-less Point (measured cost 0.58 us), so it matters only for loops that move thousands of points per frame. Low priority; the `Decimal` fixes are worth far more.

## Line 131-185 — membership tests are O(n) in the callback count (no change advised)
`ref in used_callbacks`, `cb in self.__unbound_callbacks__` and the final comprehension's `ref not in self.__callbacks__` / `ref() not in self.__unbound_callbacks__` are list scans, so the method is O(n^2) in the number of callbacks on a single Point/Angle. Typical n is 1 to 5 (a camera, a few view objects), so this is not measurable. A `set` would change the dedup semantics: weakref equality is content-based while the referent is alive (the docstring explains this was the cause of earlier errors), so hashing is not a drop-in replacement. Leave as is unless a single Point/Angle is found with dozens of listeners.

## Line 100-128 (`unbind`) — `while ref in list: list.remove(ref)` loops
Each `in` and `remove` is a scan, so unbinding an entry that has duplicates is O(n x copies), plus a second pass that prunes dead references. `unbind` runs when an object is deleted or reconnected, not per frame. Fine.

## Class-level mutable defaults (correctness note)
`__callbacks__` and `__unbound_callbacks__` are `[]` defaults on the class; a subclass that does not set them in `__init__` shares one list across all instances. The classes that mix this in set them in `__init__`; check any new user of the mixin.

## Memory
Each Point/Angle/Color carries two lists and a counter, and every callback is a `WeakMethod` (one small object each), so a bound listener adds about 100 bytes. Bounded by the number of bound listeners, not by how often a value changes.
