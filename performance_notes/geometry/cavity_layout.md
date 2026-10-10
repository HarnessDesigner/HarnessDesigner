# harness_designer/geometry/cavity_layout.py

Pure geometry for the cavity layout of a housing. The functions compute a stack geometry from a cavity count, and cavity positions on the 180-degree side of a housing. The module has one Python loop, at line 278, inside `compute_housing_cavity_geometry` (lines 143-331). That loop runs once per cavity. The function is called from `PJTHousingsTable.insert` (creation), `PJTHousing.update_cavities`, and `PJTHousing._compute_cavity_geometry` in `database/project_db/pjt_housing.py`. The first two are one-time events. How often `_compute_cavity_geometry` runs has not been checked, so it is the thing to look at before deciding this matters.

Not a concern for the current use. Revisit only if a housing with a very large cavity count shows the layout step in a profile.

Status: static read of the code only. Nothing here has been profiled.
