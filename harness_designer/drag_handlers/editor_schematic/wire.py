"""


Wire dragging is going to be a tricky one to do because of auto routing. when a
wire is routed it is OK for a wire to cross another wire but it is not OK for a
wire to sit on top of another one. a wire should not cross over a splice, housing
or terminal. wires re only allowed to be run in horizontal and vertical rrangements.
and there is going to be a strict gap that must be kept between wires when they
are running parallel to each other. wire dragging happens between waypoints, only
the section between the waypoints is what is dragged. wire will be automatically
added to the schematic view when a wire has something attached at both ends of the
wire.
"""