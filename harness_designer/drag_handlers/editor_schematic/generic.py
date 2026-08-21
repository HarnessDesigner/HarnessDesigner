"""

all dragging for any object is locked to the x and z axes.

this applies to housings and splice wires should be routed ad a housing or a
splice is moved.with housings it might be better to render an outline while the
housing is being moved and only route the wires once the new location is set.
I feel it would be far too much processing needed to try and handle that routing
realtime. the only way of doing a live update for the housings is going to be
if we can offload the wire routing work to the GPU. otherwise doing a live
preview would be really hard to do. It might be able to be done if the routing
code is written in cython or a pure C fynamic library that we can access using
ctypes.

"""