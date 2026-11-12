# Shield solder sleeves (cable shield terminations)

Started 2026-11-11 at the user's request. Related: `TWISTED_WIRE_DESIGN.md` (cables, conductors, splits).
Tick a box only when the code is written AND checked (say how: stand-in test, scratch database, or "not run in the app").

## What it is

A shielded cable (`Wire.shielded`, the cable's shield is a `pjt_cable_conductors` row with `is_shield`) is finished at a split end
with a **solder sleeve**: the shield is folded back over the jacket, the sleeve is pushed over the whole thing, heat melts the solder
ring and shrinks the tube, and the sleeve gives a **pigtail** (a wire lead) that is the shield's connection. Some sleeves come with
the pigtail already fitted ("Pre-Installed Lead"), others do not and the user adds a wire.

The catalog already has these parts: `splices` rows of type `Solder Sleeve` (TE "SolderSleeve Shield Terminators"). The catalog also
has a splice type `Solder Sleeve w/Pigtail`, which no part uses yet.

## Decisions (user, 2026-11-11)

* The sleeve is a **splice** (`pjt_splices`). A sleeve with a fitted pigtail got the type `Solder Sleeve w/Pigtail` from the builder; since 2026-11-11 the sleeves that can be used on a shielded cable have the type **`Shielding Solder Sleeve`** (see the end of this file).
* Which cable end carries a sleeve is stored on the cable: **two new nullable columns on `pjt_cables`, default NULL**
  (`start_shield_splice_id`, `stop_shield_splice_id`, each a `pjt_splices.id`).
* The sleeve needs **real depth**, so there is a **new primitive** (`shapes/sleeve.py`): a hollow, tapered tube. The coloured stripe
  (the solder ring seen through the tube) is the existing **cylinder** primitive, under it. Both are sized from the cable's diameter
  (scale), so one mesh serves every cable.
* The **pigtail is a plain wire** (user, 2026-11-11, second statement). A sleeve that comes with one gets it when it is added: its
  starting length is **twice the sleeve's length**, the user changes the length as for any wire, and the end set onto the sleeve is
  **pinned**. A sleeve without one takes whatever wire the user wants, drawn like any wire. **A sleeve with no wire on it is a snap
  point** for a wire (one: with a wire on it the sleeve refuses another).
* **Only for shielded cables.**

## Data

| where | what |
|---|---|
| `splices.min_dia` / `max_dia` (catalog) | for a solder sleeve: `min_dia` = recovered inside diameter (what it shrinks to), `max_dia` = expanded inside diameter (the largest cable it slides over). The same convention heat shrink (`bundles`) already uses. A cable of diameter *d* fits when `min_dia <= d <= max_dia`. |
| `splices.length` | TE's "Product Length" (mm) when it gives one, else 0 (the app then uses a default, see Config). |
| `splices.type` | `Solder Sleeve`, or `Solder Sleeve w/Pigtail` when TE says "Pre-Installed Lead: Yes". |
| `splices.wire_size_awg_*` / `wire_size_dia_*` | the pigtail's wire size when the part has one (TE "Pre-Installed Lead Wire Size"). |
| `pjt_cables.start_shield_splice_id` / `stop_shield_splice_id` | the sleeve on that end (NULL = none). |

## Geometry

* The sleeve sits on the cable's trunk ending AT the split plane (the jacket side of it), so it covers the end of the jacket and the
  folded shield, and the conductors leave from its far end.
* Mesh: unit outer diameter 1, length 1 along +Z, base anchored (like `shapes/cylinder.py`), scaled by (D, D, L): wall thickness and
  the taper are fractions of D. Profile (revolved): outer wall, tapered ends that shrink down onto the cable, inner wall, end rings.
* Stripe: `shapes/cylinder.py`, a silver-grey (solder) band INSIDE the wall of the tube (between its inside and outside), shorter than
  the sleeve, centred. The tube is translucent; the ring is drawn first, then the tube over it with the depth mask off.
* D = the cable's trunk diameter (clamped into `[min_dia, max_dia]` of the part) plus the wall.
* L (user, 2026-11-11: 20 mm and more was too long): the catalog `splices.length` is TE's "Product Length", the sleeve as SUPPLIED (35
  of the 72 have one: 8.5 to 55 mm, mostly about 30). It does NOT include a pre-installed lead (checked 2026-11-11 against TE's raw
  records: TE has no lead-length field, and B-023-07 / B-023-07-55-22-9 and B-023-00 / B-023-00-55-22-9, the same sleeve without and
  with a lead, have the same Product Length, 29 and 31 mm; only those two pairs exist, so it is not proved for the other pigtail parts).
  A sleeve on a cable is
  recovered (shrunk), so L = length x `RECOVERED_LENGTH` (0.8, an estimate). With no length: 3 mm + 2.5 mm per mm of the cable's
  diameter, between 10 and 24 mm (13 mm on a 4 mm cable). The constants are at the top of `shapes/sleeve.py`.

## Behaviour

0. The part search for adding opens **pre-filled with the sleeves that fit the cable** (user, 2026-11-11): the `Shielding Solder Sleeve` type and
   `min_dia <= cable diameter <= max_dia`, plus the sleeves with no sizes in the catalog (0 / 0: size not known) (stand-in test `twist/sleeve_search_test.py`, scratch SQLite).
1. Adding a sleeve (3D editor): only offered for a part whose type is a solder sleeve, only on a cable whose part is `shielded`, only
   at a split end that has no sleeve yet, only when the cable's diameter is in the part's range.
2. The sleeve's branch point is where the pigtail attaches. If the part has a pigtail, the pigtail wire is made with the sleeve
   (plain catalog wire, twice the sleeve's length, its free end for the user to connect); if not, the branch point accepts a wire snap.
3. A wire snap probe is made at a sleeve's branch point only while the sleeve has no wire (`wire_snap.check_splice_compat`).
4. The sleeve finishes the shield, so the shield conductor's own lead at that end is deleted when the sleeve is added (refused while
   anything is connected to it). Removing the sleeve does not bring it back (join the end, split it again).
5. Deleting the sleeve clears the cable's column; deleting the cable deletes its sleeves.

## Checklist

### Database building (sibling repo `harness_designer_database`)
- [x] `scrapers/te/te_tables.py` `splice()`: recovered / expanded diameters into `min_dia` / `max_dia` for solder sleeves, pigtail type (convert.py run on the raw download: 72 sleeves, all with min/max, 23 with the pigtail type)
- [x] `TE/splices.json` NOT regenerated (it holds 2,844 rows, `convert.py` writes 916 from the current raw download): `scripts/sleeve_sizes_from_te.py` copies only `min_dia` / `max_dia` / `type` of the 72 sleeve rows (167 values, nothing else in the file changed). The app's catalog database must be rebuilt (`build_database.py`) to see them.
- [x] `builder/` needs no change (it copies `min_dia` / `max_dia` / `length` as they are); `Solder Sleeve w/Pigtail` is already in `Universal/splice_types.json`

### Columns
- [x] `create_database/cables.py`: `start_shield_splice_id`, `stop_shield_splice_id` (UUID, default NULL, FK `pjt_splices`, ON DELETE SET DEFAULT = NULL)
- [x] `PJTCable`: properties, `shield_splice_id(start)` / `set_shield_splice_id(start, id)`, `delete()` deletes the sleeves; `PJTSplice.delete` clears a cable's column; `insert` passes NULL (not run in the app)
- [x] `update_fields` adds them to an existing project (scratch SQLite check, `twist/sleeve_columns_test.py`)

### Catalog part API
- [x] `global_db/splice.py`: `is_solder_sleeve`, `has_pigtail` (type, or "Pre-Installed Lead" in the description until the catalog is rebuilt), `recovered_dia` / `expanded_dia`, `fits_cable` (stand-in test `twist/sleeve_logic_test.py`)

### Primitive
- [x] `shapes/sleeve.py`: `create` / `create_vbo` (tapered hollow tube, unit size) and `sizes()` (scale of tube and ring from the cable's diameter)
- [x] registered in `shapes/__init__.py` `cache_primitives`
- [x] mesh checked (numpy, `twist/sleeve_mesh_test.py`: outer diameter 1, wall 0.1, base anchored, outward normals, scaling); not drawn in the app

### Objects and editors
- [x] 3D sleeve view (`objects_3d/splice.py`: sleeve primitive scaled by the cable's diameter + the solder ring cylinder in `render()`); NOT run in the app (no GL here)
- [x] add (3D): menu-driven, not a mouse-snap preview: the cable's right-click menu **Add Solder Sleeve (start|stop end)...** (`CableMenu`, `Cable.add_shield_sleeve`) for a shielded cable's split end with no sleeve and a part whose range fits; the sleeve follows the end (`_sync_shield_sleeve`) and goes when the end is joined or the cable deleted. NOT run in the app
- [x] pigtail wire made with a sleeve that has one (plain wire, twice the sleeve length, end on the sleeve pinned; stand-in test `twist/sleeve_pigtail_wire_test.py`; NOT run in the app)
- [x] wire snap only onto a sleeve without a pigtail (`wire_snap.check_splice_compat`, which every editor's snap / add-wire path calls); stand-in test
- [ ] peg-board view of the sleeve
- [ ] schematic: nothing (the shield's lead is drawn as a conductor)

### Docs
- [x] `MAP.md` of every directory touched (create_database, project_db, global_db, handlers, shapes, objects, objects_3d); `MEMORY.md`

## Open questions

* 600 of the 681 TE "SolderSleeve Shield Terminators" products are classified as TERMINALS by `te_classify.py` ("shield / wire terminator
  kept as a terminal"); only the 72 whose "Interconnect Device Splice Type" is `SolderSleeve` become splices. Moving the rest to splices
  would give a real catalog of sleeves but changes the terminal count: not done, waiting for the user.
* A sleeve with a pre-installed lead has no lead LENGTH in TE's data; a default (Config) is used.

* **The pigtail (user, 2026-11-11): the way the shield is connected to a terminal pin; a simple wire.** Built as: an ordinary wire
  (`pjt_wires`, no `cable_conductor_id`) whose stop end is the sleeve's branch point (a point row of its own at the split plane) and
  whose free end is twice the sleeve's length away, straight out from the cable. Its part is a plain catalog wire picked by the
  sleeve's AWG range (`Cable._pigtail_part_id`); the user can change it as any wire's. The end on the sleeve is an anchor point
  (`WireDragMixin.is_anchor_point`). When the cable moves, the sleeve is made again on the same branch point and the pigtail is put
  on it. NOT built: the peg-board view of a sleeve (the board does not draw splices); linking a wire the user snapped on to the
  shield conductor (circuits do not cross conductors yet); a lead colour for the pigtail (the scraper keeps none); a mouse preview
  while placing. The "w/Pigtail" type only decides whether the pigtail is made with the sleeve.


## 2026-11-11, third statement: sizes from TE's drawings, the type `Shielding Solder Sleeve`, the 150 mm pigtail

* **TE's catalog data for the sleeves is often wrong or missing** (user): the user read the dimensions of the customer drawings (`splices.cad`) and those are taken as correct. `harness_designer_database/scripts/sleeve_sizes_from_drawings.py` holds the figures (length, recovered, expanded diameter per part), corrected the length and diameters of 23 existing parts in `TE/splices.json` and added 3 sleeves TE files as terminals (D-106-6030, 8-1195424-4 = D-050-01, 9-1195355-4 = D-050-02); the drawings call some parts by another name than the catalog (D-101-08 = 2-1194898-2, D-104-00 = 7-1194897-0, D-050-00 = 8-1195424-2, CWT-9001 = 054955-000, CWT-9005 = 2-1190624-2).
* **The type `Shielding Solder Sleeve`** (`Universal/splice_types.json` id 10) marks the 41 sleeves whose drawing shows a plain round sleeve. The other 38 (ends of different diameters, odd shape, made for a terminal; B-023-0X is one of them, user) keep their type and are not offered for a cable: `Cable.add_shield_sleeve` and the pre-filled search take only the new type. `has_pigtail` still reads "Pre-Installed Lead" in the description for it.
* **Pigtail (user)**: a catalog sleeve that comes with one has it 150 mm long from the MIDDLE of the sleeve, and a drag cannot make it longer (`shapes/sleeve.PIGTAIL_LENGTH_MM`, `WireDragMixin._clamp_sleeve_pigtail`, 3D only). A pigtail the USER adds has no length limit, but the cable and the pigtail must both fit in the sleeve (together: cable OD + wire OD <= `max_dia`, `Splice.fits_pigtail`, checked in `wire_snap.check_splice_compat`). The old rule "twice the sleeve's length" is gone.
* Values that were NOT taken from the sheet: the expanded diameters the sheet gave for B-053-70-02 / -03 / -04 (23.5, 25.3, 19.5: lengths, not diameters); the catalog's stay. B-058-00 / -01 / -02 keep the catalog's own numbers (user: they are the correct ones). B-023-0X cannot be used (unequal ends, user): B-023-00 / -07 keep their old type and B-023-01..04 are not added (the pigtail twins B-023-00-55-22-9 / -07-55-22-9 stay shielding sleeves). 1-1194267-2 (a pigtail sleeve of drawing SO63-A-55-GA-CL, no size index) has no length. Not added: the 46 products of SO63-A-55-GA-CL and the other 550 or so shield terminators TE files as terminals, B-051-66, B-900-20/21/23 (not in TE's data).


## 2026-11-11, fourth statement: clip the shield

* A shield is connected at ONE end only (or at none: a shielded wire used as a protective jacket), so an end's shield can be cut off: **Clip Shield** (3D cable menu, `Cable.clip_shield(start)`). The state is the new integer column `pjt_cables.shield_clipped` (user): 0 neither end, 1 start, 2 stop, 3 both. Both ends can be clipped.
* **Set up like split / join (user):** the menu line changes from Clip Shield to **Unclip Shield** (`unclip_shield(start)`, which makes the shield's lead again). None of the sleeve and clip items work unless the end is split. A clipped shield greys out Add Solder Sleeve; a sleeve on the end greys out Clip Shield.
* A clipped end has no shield lead (the clip deletes it, refused while anything is connected to it; `split_end` makes none for a clipped shield). **Joining an end (split -> unsplit, user) deletes its sleeve and puts a clipped shield back to unclipped** (`join_end`). Stand-in test `twist/clip_column_test.py` (not the lead rebuild); NOT run in the app.
