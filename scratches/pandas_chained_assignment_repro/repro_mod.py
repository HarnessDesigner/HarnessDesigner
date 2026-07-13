"""Module under test.

Contains only a plain, legal column assignment on a function-local
DataFrame. This is NOT chained assignment: no intermediate object, no
mask, no second subscript. Pure Python execution of this module never
produces a ChainedAssignmentError.

Compile this exact file into a C extension with Cython and the same
statement raises a false ChainedAssignmentError, attributed to a line in
the *calling* module.
"""
import pandas as pd


def legal_assignment():
    df = pd.DataFrame({"a": [1, 2, 3]})
    df["b"] = df["a"] * 2
    return df
