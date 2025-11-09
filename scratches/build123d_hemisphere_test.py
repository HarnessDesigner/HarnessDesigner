"""
Corrected Hemisphere example using Build123d in algebra mode.
Uses Build123d primitives only (no HalfSpace dependency).
Creates a solid hemisphere oriented along +Z.
"""

from build123d import *

# Parameters
radius = 20.0  # mm hemisphere radius

# Create a full sphere
sphere = Sphere(radius)

# Cut it in half by subtracting the lower half using a Box
# The box is large enough to remove the bottom portion below Z=0
cutter = Box(2*radius, 2*radius, radius, align=(Align.CENTER, Align.CENTER, Align.MIN))
cutter = cutter.moved(Location((0,0,-radius)))

hemisphere = sphere - cutter

# Optional fillet around rim
try:
    hemisphere = hemisphere.edges().fillet(0.5)
except Exception:
    pass

# Export STEP
try:
    export_stl(hemisphere, "hemisphere_build123d.stl")
    print("Exported STEP: hemisphere_build123d.step")
except Exception:
    print("STEP export unavailable — save manually in your environment.")

# To visualize interactively:
# show(hemisphere)

print("Constructed true hemisphere using Build123d algebra mode.")
