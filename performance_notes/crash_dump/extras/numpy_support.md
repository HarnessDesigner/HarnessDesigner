# harness_designer/crash_dump/extras/numpy_support.py

render(value) for numpy.ndarray — the only place in crash_dump that ever imports numpy, and only once a value of this type is actually captured. Large arrays are summarized rather than enumerated element by element: {'shape': ..., 'dtype': ..., 'preview': <first 20 flattened items>, 'truncated': <bool>}.

Cold path (28 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
