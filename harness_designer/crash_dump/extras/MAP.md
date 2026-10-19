## FILES

#### __init__.py

Docstring-only — explains the lazy-import contract: each submodule here is only ever imported by
`../render.py` the first time a value of its specific type is actually captured, so importing `crash_dump`
itself never forces importing numpy or anything else the host app doesn't otherwise use.

#### datetime_support.py

`render(value)` for `datetime.datetime`/`datetime.date` — returns `('value', value.isoformat())`.

#### decimal_support.py

`render(value)` for `decimal.Decimal` — returns `('value', str(value))`.

#### numpy_support.py

`render(value)` for `numpy.ndarray` — the only place in `crash_dump` that ever imports numpy, and only once
a value of this type is actually captured. Large arrays are summarized rather than enumerated element by
element: `{'shape': ..., 'dtype': ..., 'preview': <first 20 flattened items>, 'truncated': <bool>}`.

#### uuid_support.py

`render(value)` for `uuid.UUID` — returns `('value', str(value))`.
