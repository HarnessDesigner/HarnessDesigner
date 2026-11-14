# harness_designer/handlers/concentric_handler.py

Finds the concentric a bundle or branch uses and adds wires to it; builds the cross-section spec for the widget. All user-action frequency (drop a wire on the section widget, open the section), none per frame.

## Line 183-209 (`find_concentric_for_bundle`, `find_concentric_for_branch`), 233-284 (`_entries`, `needs_plan`, `replan`)
Loops over the concentric layers and wire rows with `select` calls (answered from the in-memory table store, see `database/README.md`) and a sort per layer. `replan` re-plans the packing when wires change; its cost is the packing in `ui/concentric_section/packing.py`, which is the part to look at if a section with many wires is slow.

## Line 330-356 (`build_section`)
Builds the `SectionSpec` and one `WireDetail` per wire (`_detail_for`, `_cable_for`, `_gauge_text`) on each call. Called when the section widget opens or refreshes; cache it only if a profile shows repeated rebuilds while a dock is open.
