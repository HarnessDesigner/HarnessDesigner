# harness_designer/handlers/terminal_handler.py

## Line 44-260 (`_terminal_extent`, `_female_terminal_position`, `_male_terminal_position`, `free_end_position`, ...) — geometry helpers
Each computes a terminal's position from its part dimensions and a few vector operations. Called when a terminal is placed or repositioned, and from the snap probes. Cheap per call; a probe set may call them once per candidate terminal.

## Line 262-290 (`reposition_from_model`) — reads the terminal's model and writes its position
Runs when a terminal's 3D model becomes available. Not per frame.

## Line 333-400 (`_is_generic_model`, `_extract_blade_size_from_description`, `estimate_dimensions`) — parsing and catalog reads
`_extract_blade_size_from_description` tokenises a description string. `estimate_dimensions` runs on the part editor's request, not per frame. Fine.

## Line 484-486 (`estimate_dimensions`, inside the loop over `mainframe.project.cavities`) — linear scan of project cavities
A loop over every project cavity, with a per-cavity check of its compatible terminals. Runs on demand, once per request. Linear in the number of cavities; fine at current sizes.
