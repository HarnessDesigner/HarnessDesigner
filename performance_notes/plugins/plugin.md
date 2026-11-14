# harness_designer/plugins/plugin.py

Plugin base class + start_registration(instance). The _PluginMeta metaclass attaches whatever RegisterPlugin instance was just handed to start_registration() onto the *next* Plugin subclass defined — cls._registration = _registering runs in _PluginMeta.__init__, which fires for every class statement using this metaclass.

Cold path (36 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
