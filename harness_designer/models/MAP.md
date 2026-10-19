## FILES

#### deutsch terminal female solid.stl

Fallback 3D model for Deutsch-family female terminals. `objects/objects_3d/terminal.py`'s `Terminal`
hardcodes this file for a specific set of Deutsch part-number prefixes (e.g. `0462-004`, `0462-005`,
`0462-006`, `0462-201`, `0462-203`) when no vendor-supplied `model3d` exists for that part.

#### deutsch terminal male solid.stl

Same mechanism as the female file above, for male Deutsch part-number prefixes (e.g. `2362989-1`,
`5960-203-04141`, `0460-256`, `0460-002`, `0460-010`, `0460-202`, `0460-204`).

#### generic terminal female 1.2.stp

Generic fallback STEP model for a female terminal, blade size 1.2 mm. See "generic terminal male 1.2.stp"
below for the shared mechanism every `generic terminal <gender> <size>[ round].stp` file follows.

#### generic terminal female 1.5.stp

Generic fallback STEP model for a female terminal, blade size 1.5 mm. Same mechanism as the other
`generic terminal *` files — see "generic terminal male 1.2.stp" below.

#### generic terminal female 2.6 round.stp

Generic fallback STEP model for a female terminal, round pin size 2.6 mm. Same mechanism as the other
`generic terminal *` files — see "generic terminal male 1.2.stp" below.

#### generic terminal female 2.8.stp

Generic fallback STEP model for a female terminal, blade size 2.8 mm. Same mechanism as the other
`generic terminal *` files — see "generic terminal male 1.2.stp" below.

#### generic terminal female 4.8.stp

Generic fallback STEP model for a female terminal, blade size 4.8 mm. Same mechanism as the other
`generic terminal *` files — see "generic terminal male 1.2.stp" below.

#### generic terminal female 6.3.stp

Generic fallback STEP model for a female terminal, blade size 6.3 mm. Same mechanism as the other
`generic terminal *` files — see "generic terminal male 1.2.stp" below.

#### generic terminal male 1.2.stp

Generic fallback STEP model for a male terminal, blade size 1.2 mm. All `generic terminal <gender>
<size>[ round].stp` files (female and male, this one and the ones below/above) follow the same mechanism:
`Terminal.__init__` (`objects/objects_3d/terminal.py`) builds the filename as `f'generic terminal {gender}
{blade_size}[ round].stp'` from the part's own `gender`/`blade_size` fields (the `" round"` suffix is added
for round-pin sizes) and, if a file by that exact name exists in this directory, inserts it as the part's
`model3d` when the part itself has no specific vendor-supplied 3D model — i.e. this whole directory
(`_GENERIC_MODEL_PATH`, also referenced the same way from `handlers/terminal_handler.py`) is a last-resort,
size-matched placeholder shape library, not real manufacturer models. Not Python source; `.stp` is a STEP
3D geometry file read by the app's model-loading pipeline (`resources.py`/`model_process.py`), not by
anything in this directory itself.

#### generic terminal male 1.5.stp

Generic fallback STEP model for a male terminal, blade size 1.5 mm. Same mechanism as "generic terminal
male 1.2.stp" above.

#### generic terminal male 10.0.stp

Generic fallback STEP model for a male terminal, blade size 10.0 mm. Same mechanism as "generic terminal
male 1.2.stp" above.

#### generic terminal male 2.4 round.stp

Generic fallback STEP model for a male terminal, round pin size 2.4 mm. Same mechanism as "generic
terminal male 1.2.stp" above.

#### generic terminal male 2.6 round.stp

Generic fallback STEP model for a male terminal, round pin size 2.6 mm. Same mechanism as "generic
terminal male 1.2.stp" above.

#### generic terminal male 2.8.stp

Generic fallback STEP model for a male terminal, blade size 2.8 mm. Same mechanism as "generic terminal
male 1.2.stp" above.

#### generic terminal male 4.8.stp

Generic fallback STEP model for a male terminal, blade size 4.8 mm. Same mechanism as "generic terminal
male 1.2.stp" above.

#### generic terminal male 6.3.stp

Generic fallback STEP model for a male terminal, blade size 6.3 mm. Same mechanism as "generic terminal
male 1.2.stp" above.

#### generic terminal male 6.35.stp

Generic fallback STEP model for a male terminal, blade size 6.35 mm. Same mechanism as "generic terminal
male 1.2.stp" above.
