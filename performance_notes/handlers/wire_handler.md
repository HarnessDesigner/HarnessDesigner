# harness_designer/handlers/wire_handler.py

## Line 54-101 (`_wire_cross_search_params`, `terminal_wire_search_params`, `splice_wire_search_params`) — search-box seeds
Each builds a small `SearchParameters` object from a terminal's or splice's crimp range. Runs when the user opens a search dialog. No database reads; the search itself runs in the dialog. Fine.

Module docstring records why the earlier version was replaced: it pre-fetched every matching part number, which could run into thousands and crash the dialog. The replacement is a range filter, so this module no longer scales with the size of the wires table.
