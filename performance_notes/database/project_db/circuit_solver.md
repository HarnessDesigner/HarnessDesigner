# harness_designer/database/project_db/circuit_solver.py

Pure numeric solver (no database access). Runs when a circuit changes or the circuit dock refreshes, not per frame.

## Line 551-715 (`solve_circuit`), 851-910 (`solve_bundled`) — iterates until temperatures settle
Per solve: a walk over the circuit tree and repeated passes (`_linear_pass`, line 464) until the temperatures and constant-power currents stop moving, each pass touching every member with a few float operations. Cost is O(members x iterations), with iterations typically a handful. `solve_bundled` solves circuits that share a bundle together, so a project with one big bundle shared by many circuits solves them as one system (O(total members x iterations)). In plain Python this is microseconds per member; a 500-member system is a few milliseconds per iteration. If the circuit dock re-solves on every edit of a large project, solve only the circuits whose members changed (they are independent unless they share a bundle).

## Line 356-417 (`calibrate_theta`), 738-847 (`bundle_derating_factor`, `bundle_adjusted_parts`)
Run once per wire per solve; they sort the manufacturer's limits (a few rows) each time. A per-wire cache of the calibrated `theta` would remove repeated sorts, at a few floats of memory per wire, but it is only worth doing if profiling shows the solve is hot.
