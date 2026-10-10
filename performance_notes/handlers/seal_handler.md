# harness_designer/handlers/seal_handler.py

## Line 38-59 (`_find_attached_wire_part`) — one SQL query per call
Runs `SELECT part_id FROM pjt_wires WHERE start_point3d_id=? OR stop_point3d_id=?` every time it is called. It is also called once more on each `terminal_seal_search_params` call. The `wire_point3d_id` lookup on line 43-44 is a second query for the same terminal. Two queries per call; the number of calls depends on the caller.

## Line 124-165 (`wire_seal_fit_ok`) — one fit check per candidate terminal during hover
The docstring says this runs once per candidate terminal during an interactive snap session, to choose a highlight colour. Each call calls `_find_attached_wire_part`, so each hover over a candidate costs the two SQL queries above. If a session checks many terminals per mouse move, this is the cost to watch. Caching the attached-wire lookup per terminal for the length of one session would remove the repeat queries.

## Line 61-121 (`terminal_seal_search_params`) — builds search params on demand
Runs when the user opens a search, not per frame. Fine.
