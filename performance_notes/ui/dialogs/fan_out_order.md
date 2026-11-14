# harness_designer/ui/dialogs/fan_out_order.py

FanOutOrderDialog -- the order a split cable end's conductors fan out in: a list with Move Up / Move Down; GetValue() returns, for each new place, the index the conductor had in the list given. Opened from the 3D cable menu (objects_3d/cable.py CableMenu.on_fan_out), applied by objects.cable.Cable.set_fan_order.

Cold path (110 lines): the AST pass finds no per-frame or per-event handlers, no nested loops, no loops that allocate Qt or NumPy objects, no timers and no threads. It runs when its feature is opened or used, so there is nothing here worth optimising.

Status: static read of the code only. Nothing here has been profiled.
