# Title

BUG: False ChainedAssignmentError, misattributed to the caller, when setitem runs in Cython-compiled code — and no supported way to disable the check

---

# Body

### Pandas version checks

- [x] I have checked that this issue has not already been reported.
- [x] I have confirmed this bug exists on the latest version of pandas.
- [ ] I have confirmed this bug exists on the main branch of pandas.

### Reproducible Example

Two files. `repro_mod.py` contains only a plain, legal column assignment on
a function-local DataFrame — no mask, no intermediate object, no second
subscript:

```python
# repro_mod.py
import pandas as pd


def legal_assignment():
    df = pd.DataFrame({"a": [1, 2, 3]})
    df["b"] = df["a"] * 2
    return df
```

```python
# run_repro.py
import warnings

import pandas as pd

import repro_mod

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    df = repro_mod.legal_assignment()

assert df["b"].tolist() == [2, 4, 6]  # the assignment itself worked fine

chained = [w for w in caught
           if issubclass(w.category, pd.errors.ChainedAssignmentError)]

if not chained:
    print("OK: no warning")
else:
    for w in chained:
        print(f"FALSE POSITIVE: {w.category.__name__} "
              f"attributed to {w.filename}:{w.lineno}")
```

Run it twice — once with the module as plain Python, once after compiling
that same module into a C extension with Cython:

```
$ python run_repro.py
OK: no warning

$ cythonize -3 -i repro_mod.py
$ python run_repro.py
FALSE POSITIVE: ChainedAssignmentError attributed to ...\run_repro.py:10
```

Identical source, identical runner. Note the attribution: `run_repro.py:10`
is `df = repro_mod.legal_assignment()` — the *caller*, which performs no
assignment at all. In a larger application this misattribution points at
whatever pure-Python frame happens to sit below the compiled code (in ours,
the application's `MainLoop()` call in the entry module), which makes the
warning extremely hard to trace back to its real origin.

### Issue Description

`DataFrame.__setitem__` (pandas 3.0.3, `pandas/core/frame.py:4642`; the same
pattern guards every `ChainedAssignmentError` site in `frame.py`,
`series.py`, `generic.py`, and `indexing.py`) detects chained assignment
with two heuristics:

```python
if not CHAINED_WARNING_DISABLED:
    if sys.getrefcount(self) <= REF_COUNT and not com.is_local_in_caller_frame(self):
        warnings.warn(_chained_assignment_msg, ChainedAssignmentError, stacklevel=2)
```

Both heuristics assume the caller is interpreted CPython code, and both
misfire when the caller is a compiled extension:

1. **Refcount** — a Cython function keeps `df` in a C variable rather than
   in a frame's locals, so `sys.getrefcount(df)` inside `__setitem__` sits
   at the temporary-object level even though `df` is a genuine local.
2. **Frame inspection** — `is_local_in_caller_frame`
   (`pandas/core/common.py:662`) looks for the object in
   `sys._getframe(2).f_locals`. Cython functions do not create Python frame
   objects, so `sys._getframe(2)` skips past the real caller entirely and
   lands on an unrelated pure-Python frame further down the stack. The
   rescue check fails, and `stacklevel=2` attributes the warning to that
   unrelated frame.

The same failure mode applies to any frame-less caller (Cython, mypyc, and
similar ahead-of-time compilers).

Filtering the warning is not a real workaround: with
`warnings.filterwarnings("ignore", category=ChainedAssignmentError)` the
message disappears but the detection machinery still runs. Because the
refcount test always passes for compiled callers, **every** setitem from
compiled code takes the slow path — `sys._getframe(2)`, a full `f_locals`
materialisation, and the `warnings` machinery. We measured roughly 4 µs per
assignment on small frames (Python 3.11, Windows) — a permanent tax on
exactly the code that was compiled for speed.

A short-circuit for this already exists: `CHAINED_WARNING_DISABLED`
(`pandas/compat/_constants.py`) skips the whole block, including both
heuristics. But it is a constant computed from the interpreter type
(`= PYPY`) — informational only, with no supported way for an application
to set it.

Suggested fix — either or both:

- Provide a supported opt-out that feeds `CHAINED_WARNING_DISABLED`, e.g.
  an environment variable (`PANDAS_CHAINED_WARNING_DISABLED=1`), mirroring
  how `PANDAS_COPY_ON_WRITE` was handled during the CoW rollout.
- Suppress the warning when frame inspection cannot positively identify the
  caller (i.e. when the frame walk cannot see the object at all): a
  heuristic that cannot observe its evidence should not fire.

### Expected Behavior

A plain `df["b"] = ...` on a function-local DataFrame should not raise
`ChainedAssignmentError` regardless of whether the enclosing function is
interpreted or compiled — and applications embedding pandas in compiled
code should have a supported way to opt out of the detection overhead
entirely.

### Installed Versions

<details>

```
INSTALLED VERSIONS
------------------
commit                : 72f2fea91530b5abb3cf2100cb22d84e504695c0
python                : 3.11.14
python-bits           : 64
OS                    : Windows
OS-release            : 10
Version               : 10.0.22621
machine               : AMD64
processor             : AMD64 Family 23 Model 49 Stepping 0, AuthenticAMD
byteorder             : little
LC_ALL                : None
LANG                  : None
LOCALE                : English_United States.1252

pandas                : 3.0.3
numpy                 : 2.2.6
dateutil              : 2.9.0.post0
pip                   : 26.0.1
Cython                : 3.2.4
```

</details>
