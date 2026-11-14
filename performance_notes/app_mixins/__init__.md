# harness_designer/app_mixins/__init__.py

Facade only: imports `callback_mixin` and re-exports 1 name(s). There is no per-call cost.

The cost is import time: importing this package imports those modules and everything they import, so it decides how much loads at startup and in what order. The trailing `del _alias` lines remove the module alias from this namespace only; the modules stay in `sys.modules`, so they save no memory.
