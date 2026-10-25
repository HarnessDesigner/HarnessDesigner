## FILES

#### __init__.py

Re-exports `generic`/`material`/`metallic`/`plastic`/`polished`/`rubber`/`glowing`. The public
constructors — `materials.Plastic(color)`/`.Metallic(color)`/`.Polished(color)`/`.Rubber(color)`/
`.Generic(color)`/`.Glowing(color)`, each a single-`Color`-arg constructor — are unchanged across
the 2026-09-15 rewrite and are exactly what all 61 existing call sites already used (confirmed via
`dep_trace.py --imported-by`); none of those call sites needed changes. `materials.Circuit` (2026-10-25) is `circuit.CircuitMaterial`, built with no argument.

#### circuit.py

`CircuitMaterial(GlowingMaterial)` -- what every member of a selected circuit is shown with (`materials.Circuit()`: emissive amber, `COLOR`). `objects.circuit.Circuit.highlight` hands it to `identify()` on each member, and `identify(None)` restores the member's own material. The colour is a class constant, not a `Config.colors` entry. Added 2026-10-25.

#### generic.py

`GenericMaterial(GLMaterial)` — a pure declarative weight-set subclass, no `__init__` override
needed.

#### glowing.py

`GlowingMaterial(GLMaterial)` — the one material subclass that does override `__init__` (extends
via `super().__init__()`), adding an emissive term on top of the same base ambient/diffuse/specular
fill every other material shares.

#### material.py

`GLMaterial` — the base class, and the whole rewrite's actual fix (rebuilt from scratch
2026-09-15 at the user's request: "the system I have currently ends up changing the actual color
that is seen"). Root-caused to three compounding issues in the old design, all fixed here: (1) each
old material subclass invented its own ad hoc ambient/diffuse/specular RGB formula, several mixing
in a fixed colorless constant (flat grey specular/ambient floor) that desaturated/tinted the true
color by an amount that varied per material class; (2) the fragment shaders summed
ambient+diffuse+specular and let the GPU's implicit **per-channel** clamp-on-write handle overflow,
which shifts hue whenever the sum overflows unevenly across channels — common, since the scene
light plus the (intentionally non-neutral, warm-tinted) headlight can each add close to
full-strength contributions on the same lit face; (3) the offline ray tracer's own `Material`
struct already modeled ambient/diffuse/specular as plain scalar multipliers on the true color, so
the rasterizer's RGB-triple scheme was inconsistent with its own sibling renderer. **Current
design**: every material type is just a handful of scalar weights (`_ambient_weight`/
`_diffuse_weight`/`_specular_weight`/`_metallic`/`_shine`, plus `_cl_roughness`/`_cl_reflectivity`/
`_cl_ior` for the ray tracer) applied directly to the caller's own `Color` — ambient/diffuse are
the true color times one scalar (same scalar every channel, so hue can never shift on its own);
specular is a per-channel lerp between neutral white and the true color driven by `_metallic`
(0.0 dielectric = white highlight, 1.0 metal = highlight tinted by the material's own color — the
one intentional place hue *can* shift, confined to the shininess-exponent hot spot). Exposes
`cl_array` (the ray tracer's unchanged 12-float layout, now populated from these same weights
instead of an averaged RGB triple), `color_scalar`, `is_opaque`, and `set(program)`, which pushes
the computed values onto whichever of `FacesProgram`/`EdgesProgram` it's handed. Both fragment
shaders were also changed to divide all 3 channels by the peak channel together when it exceeds
1.0, instead of relying on the implicit per-channel clamp — preserves hue on overflow for every
material, not just the new ones (skipped deliberately for the faces shader's emissive glow branch,
which is allowed to run hot). **How to apply:** when tuning a material's look, change its weight
constants — never reintroduce a hardcoded RGB triple or a flat colorless additive constant; that
is exactly the anti-pattern this rewrite removed. If a rendered color still looks off, suspect the
light config (`Config.editor_3d.lighting`/`.headlight`) or a genuinely new overflow case before
reintroducing per-material color hacks.

#### metallic.py

`MetallicMaterial(GLMaterial)` — pure declarative weight-set subclass, no `__init__` override
needed.

#### plastic.py

`PlasticMaterial(GLMaterial)` — pure declarative weight-set subclass, no `__init__` override
needed. The old hardcoded color-preset subclasses that used to live here
(`BlackPlasticMaterial`/`CyanPlasticMaterial`/`RedPlasticMaterial`/etc.) were confirmed dead via
`dep_trace.py --calls` (never constructed anywhere) and deleted outright during the 2026-09-15
rewrite, not ported forward.

#### polished.py

`PolishedMaterial(GLMaterial)` — pure declarative weight-set subclass, no `__init__` override
needed.

#### rubber.py

`RubberMaterial(GLMaterial)` — pure declarative weight-set subclass, no `__init__` override
needed.
