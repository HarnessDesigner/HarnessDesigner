# harness_designer/monkey_patch.py

`get_offsets` is a no-op that returns four zeros, kept only so an old import still resolves (the wx-era window-border workaround is not needed under Qt). No cost. If nothing imports it any more it can be deleted, which also saves one import at startup.
