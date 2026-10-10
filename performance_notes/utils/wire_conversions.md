# harness_designer/utils/wire_conversions.py

## Line 76-126 (`_get_strand_count`, `_get_packing_factor`) — table lookup with interpolation
`_get_packing_factor` sorts the table keys on every call (line 112) and then scans them to interpolate. The table is small and the function is called from diameter conversions, so the cost is negligible. Caching the sorted keys once at import would make it tidier.

## Line 127-200 (`_solid_to_bundle`, `_bundle_to_solid`, `mm2_to_awg`, `awg_to_mm2`) — arithmetic conversions
Scalar formulas with a few divisions and square roots. Called for each wire when diameters are shown or computed. Cheap.

## Line 213-end (`awg_to_d_in`, `awg_to_d_mm`, `d_in_to_d_mm`, `d_mm_to_mm2`, `mm2_to_d_mm`, `mm2_to_d_in`, `d_mm_to_awg`) — conversion family
Each one converts through a shared formula. Scalar work. The `strands` argument is an estimate hint in some functions and is ignored in others (per the docstrings). Fine.

**Note:** the conversions accept `float | _d` (a decimal type). Mixed use of decimal and float in one calculation is a precision consideration, not a performance one.
