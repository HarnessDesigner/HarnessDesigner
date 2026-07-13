# False ChainedAssignmentError when `df[col] = ...` runs in Cython-compiled code

Minimal reproduction for a pandas bug report.

## Summary

A plain, legal column assignment on a function-local DataFrame

```python
def legal_assignment():
    df = pd.DataFrame({"a": [1, 2, 3]})
    df["b"] = df["a"] * 2
    return df
```

raises a **false `ChainedAssignmentError`** when the module containing it is
compiled into a C extension with Cython, and the warning is **misattributed
to a line in the calling module** that contains no assignment at all.
The same module executed as pure Python is silent. The assignment itself
works correctly in both cases; only the diagnostic is wrong.

## Reproduce

Requirements: pandas 3.x, Cython, a C compiler.

```
pip install pandas cython

# 1. pure Python - no warning
python run_repro.py

# 2. compile the module in place, run the identical runner again
cythonize -3 -i repro_mod.py        # or: python -m Cython.Build.Cythonize -3 -i repro_mod.py
python run_repro.py
```

## Observed output

Step 1 (pure Python):

```
OK: no warning (expected for pure-Python repro_mod)
```

Step 2 (same code as a compiled extension):

```
FALSE POSITIVE: ChainedAssignmentError attributed to ...\run_repro.py:22
A value is being set on a copy of a DataFrame or Series through chained assignment.
...
```

(`run_repro.py:22` is `df = repro_mod.legal_assignment()` - the caller,
which performs no assignment.)

Reproduced with: Python 3.11.14 (Windows, MSC v.1944 64 bit), pandas 3.0.3,
Cython 3.2.4.

## Root cause

`DataFrame.__setitem__` (pandas 3.0.3, `pandas/core/frame.py:4642`) decides
"chained assignment" from two heuristics:

```python
if not CHAINED_WARNING_DISABLED:
    if sys.getrefcount(self) <= REF_COUNT and not com.is_local_in_caller_frame(self):
        warnings.warn(_chained_assignment_msg, ChainedAssignmentError, stacklevel=2)
```

Both assume the caller is interpreted CPython code:

1. **Refcount** - a Cython function keeps `df` in a C variable, not in a
   frame's locals, so `sys.getrefcount(df)` inside `__setitem__` is at the
   temporary-object level (<= REF_COUNT) even though `df` is a genuine local.
2. **Frame inspection** - `is_local_in_caller_frame`
   (`pandas/core/common.py:662`) checks `sys._getframe(2).f_locals` for the
   object. Cython functions do not create Python frame objects, so
   `sys._getframe(2)` skips past the real caller and lands on whatever pure
   Python frame is further down the stack. `df` is of course not a local
   there, so the rescue check fails, and `warnings.warn(..., stacklevel=2)`
   attributes the warning to that unrelated frame.

The same failure mode applies to any frame-less caller (Cython, mypyc, and
similar compilers), and to every `ChainedAssignmentError` site guarded this
way (`frame.py`, `series.py`, `generic.py`, `indexing.py`).

## Why filtering the warning is not a fix

`warnings.filterwarnings("ignore", category=pd.errors.ChainedAssignmentError)`
suppresses the message but the detection machinery still runs on **every**
setitem from compiled code: because the refcount test always passes there,
every assignment takes the slow path - `sys._getframe(2)` plus a full
`f_locals` materialisation plus the `warnings` machinery. Measured at
roughly 4 microseconds per assignment on small frames (Python 3.11,
Windows) - a permanent tax on exactly the code that was compiled for speed.

`CHAINED_WARNING_DISABLED` (`pandas/compat/_constants.py`) already exists
and short-circuits all of this, but it is a constant (`= PYPY`) computed
from the interpreter type; there is no supported way for an application to
set it.

## Suggested fix

Either (or both):

- Provide a supported opt-out that feeds `CHAINED_WARNING_DISABLED`, e.g.
  an environment variable (`PANDAS_CHAINED_WARNING_DISABLED=1`), mirroring
  how `PANDAS_COPY_ON_WRITE` was handled during the CoW rollout.
- Skip the warning when the caller cannot be positively identified, i.e.
  when frame inspection cannot see the object at all - a heuristic that
  cannot observe its evidence should not fire.
