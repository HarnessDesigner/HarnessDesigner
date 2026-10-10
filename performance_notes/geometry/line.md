# harness_designer/geometry/line.py

A `Line` is two `Point`s with projection helpers, and the module has no Python loops. Projection and distance tests are a few numpy operations each. The cost per call is numpy call overhead plus one allocation per returned `Point`.

Where `Line` is used on a hot path (for example, the snap and projection code in the wire drags), the calls are per mouse move. Batching several projections into one numpy operation would cut the overhead, but only if the calls are shown to dominate. Not profiled.

Status: static read of the code only. Nothing here has been profiled.
