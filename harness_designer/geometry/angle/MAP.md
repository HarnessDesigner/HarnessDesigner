## FILES

#### __init__.py

Package marker for `geometry/angle/`; no logic of its own. The package holds `Angle` and
`Quaternion` — the rotation half of the `Point`/`Angle` reactive pair documented in
`geometry/MAP.md`; read that file's "Point/Angle callback system" section first, since it applies
equally here. Both `Angle` and `Quaternion` use the same metaclass-interning-via-weakref pattern
seen in `geometry/point.py`'s `PointMeta` (here, `AngleMeta`) — changes to one half of that
pattern (e.g. how instances get garbage-collected and deregistered) likely need the mirrored
change in the other.

#### angle.py

`Angle` — a `CallbackMixin`-backed, metaclass-managed (`AngleMeta`) rotation value, internally
backed by a `Quaternion`. `AngleMeta.__call__` interns/tracks instances via weakrefs
(`_remove_instance`), mirroring `PointMeta`. Full operator overloading (`__iadd__`/`__add__`,
`__isub__`/`__sub__` compose rotations; `__matmul__`/`__rmatmul__` apply the rotation to a
`Point`/numpy array) plus a numpy `__array_ufunc__` hook. `x`/`y`/`z` properties expose/set
Euler-angle components, backed by `__update_quat`/`__update_matrix` keeping the internal
quaternion and cached rotation matrix in sync. Conversions: `as_euler_*`, `as_quat_*`,
`as_matrix_float`/`as_matrix_numpy` — the latter is **column-vector** convention (`R @ v`), while
the rest of the codebase applies rotations in **row-vector** convention (`v @ R.T`) via numpy `@`;
see `geometry/MAP.md`'s "rotation matrix convention" entry for the real bug this caused, and apply
that same convention in any new transform cache built from this property rather than the matrix's
own "natural" `R @ v` reading. Construction: `from_direction`, `from_euler`, `from_quat`,
`from_matrix`, `from_points`, `from_frame`, `from_axis_angle`. **`inverse()` and `__neg__` are two
separate, distinct operations** (lines 263 and 281) — see the package-wide negation/inverse note
below before treating them as interchangeable.

#### quaternion.py

`Quaternion` — the plain (non-metaclass, non-callback) quaternion value type `Angle` wraps. Full
operator overloading (`__iadd__`/`__add__`, `__isub__`/`__sub__`, `__mul`/private multiply,
`__itruediv__`/`__truediv__`, `__matmul__`/`__rmatmul__` to rotate a `Point`/array), a numpy
`__array_ufunc__` hook, `__enter__`/`__exit__` (batched-mutation context manager, same idiom
`Point`'s equivalent uses), `__normalize()` (internal renormalization after arithmetic), and
conversions (`as_numpy`/`as_float`/`as_decimal`). **`conj()` (line 635), `__neg__` (line 647), and
`negation()` (line 695) are three distinct operations, not drop-in substitutes for each other
despite all "flipping" the rotation in some sense** — alongside `Angle.inverse()`/`Angle.__neg__`
above, that's four related-but-different operations across the two files. Before using any of
`inverse`/`negation`/`conj`/unary `-` interchangeably, check which one the surrounding code
actually needs (MEMORY.md flags this exact confusion risk explicitly; if the precise semantic
difference isn't already clear from reading both implementations side by side, ask rather than
assume). Type hints throughout this file (and `angle.py`) are concrete (`'Angle'`, `'Quaternion'`,
`np.ndarray`, etc.), including quoted forward-references inside `TYPE_CHECKING`-only imports (e.g.
`_line.Line`, `_point.Point`) — consistent with the codebase-wide Cython rule that every
`@property` return type and operator-dunder return type must name the most specific concrete
class, since this whole package compiles to a C extension for release builds and a weakened hint
(base class, `TypeVar`/`Generic`) silently loses Cython's specialization for that value.
