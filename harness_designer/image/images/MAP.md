## FILES

#### download_0.png

#### download_1.png

#### download_2.png

#### download_3.png

#### download_4.png

#### download_5.png

#### header.png

#### header_1200x80.png

#### header_600x80.png

#### icon_256x256.png

#### large_splash.png

#### loop_layer1.png ... loop_layer9.png

The nine layers of the wire-LOOP preview that `ImageLoader.build_wire_loop` composites: layers 1, 4 and 7 are recoloured
to the wire colour, 2, 5 and 8 to the stripe colour (skipped when there is no stripe), 3, 6 and 9 are drawn as they are.

#### no_image.png

#### small_splash.png

#### twisted2_base_1.png, twisted2_base_2.png

Insulation of each wire of a twisted PAIR (white mask, recoloured): what is visible of that wire, already cut where
the other wire crosses over it, so the two never overlap and the draw order does not matter.

#### twisted2_stripe_1.png, twisted2_stripe_2.png

The stripe of each wire of the pair: one layer per wire, so wire 1 only, wire 2 only or both striped is just which
layers are drawn (and each can have its own colour). The stripe turns with the wire, so it shows as a helix.

#### twisted2_conductor_1.png, twisted2_conductor_2.png

The bare end of each wire of the pair, from the end of the insulation (x = 300) to the right edge. One layer per wire so
the two cores can be different colours.

#### twisted2_shadow.png

Black layer with alpha only: edge shading of both wires and the soft shadow where one lies against the other, plus the
shading of the bare ends. Drawn last.

#### twisted3_base_1.png, twisted3_base_2.png, twisted3_base_3.png

As `twisted2_base_*` for a twisted TRIPLE.

#### twisted3_stripe_1.png, twisted3_stripe_2.png, twisted3_stripe_3.png

As `twisted2_stripe_*` for a twisted triple.

#### twisted3_conductor_1.png, twisted3_conductor_2.png, twisted3_conductor_3.png

As `twisted2_conductor_*` for a twisted triple (the three bare ends leave at different heights).

#### twisted3_shadow.png

As `twisted2_shadow.png` for a twisted triple.

#### cable_jacket.png, cable_jacket_shadow.png

Outer jacket of a multi-conductor cable (mask to recolour, and its shading), x = 0 to 170, full height. Drawn over the
conductors.

#### cable_shield.png, cable_shield_shadow.png

Exposed braid shield (x = 155 to 235, 84 px across), an opaque tube to recolour; the weave is in the shadow layer. Drawn
between the conductors and the jacket.

#### cable_shield_bare.png, cable_shield_bare_shadow.png

The same braid for a shielded cable with NO jacket: it starts at the left edge and has no shadow from a jacket end.

#### coax_jacket.png, coax_jacket_shadow.png

Outer jacket of a coax cable, x = 0 to 140.

#### coax_shield.png, coax_shield_shadow.png

Exposed braid of a coax cable (x = 125 to 215, 62 px across).

#### wire_base.png

#### wire_conductor.png

#### wire_shadow.png

#### wire_stripe.png

The `twisted2_*`, `twisted3_*`, `cable_*` and `coax_*` files are generated: run `python diagnostics/make_wire_layers.py`
(it only writes those names) rather than editing them by hand. They are assembled by `image/wire_images.py`.
