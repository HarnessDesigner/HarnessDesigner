"""Runner. Execute twice:

1. With repro_mod as plain Python -> prints "OK: no warning".
2. After compiling repro_mod with Cython (see README) -> prints a false
   ChainedAssignmentError, misattributed to a line in THIS file, which
   contains no assignment at all.
"""
import sys
import warnings

import pandas as pd

import repro_mod

print(f"python  {sys.version}")
print(f"pandas  {pd.__version__}")
print(f"module  {repro_mod.__file__}")
print()

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    df = repro_mod.legal_assignment()

assert df["b"].tolist() == [2, 4, 6]  # the assignment itself worked fine

chained = [w for w in caught
           if issubclass(w.category, pd.errors.ChainedAssignmentError)]

if not chained:
    print("OK: no warning (expected for pure-Python repro_mod)")
else:
    for w in chained:
        print(f"FALSE POSITIVE: {w.category.__name__} "
              f"attributed to {w.filename}:{w.lineno}")
        print(w.message)
