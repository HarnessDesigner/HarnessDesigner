# TODO: Housing attributes panel

'''
part_number str
description str
manufacturer Manufacturer gloabl_db.manufacturer_table.choices
family str gloabl_db.families_table.choices
series str gloabl_db.series_table.choices
direction str gloabl_db.directions_table.choices
min_temp str gloabl_db.temperatures_table.choices
max_temp str gloabl_db.temperatures_table.choices
color Color
length _decimal
width _decimal
height _decimal
weight _decimal
cavity_lock str

compat_covers list[_cover.Cover]
compat_cpas list[_cpa_lock.CPALock]
compat_tpas list[_tpa_lock.TPALock]
compat_terminals list[_terminal.Terminal]
compat_seals list[_seal.Seal]
mates_to list["Housing"]

ip_rating ip.IPRating
terminal_sizes list[float]
sealed bool
centerline _decimal
rows int
num_pins int
dxf Resource

cad
image
datasheet
model3d

'''
