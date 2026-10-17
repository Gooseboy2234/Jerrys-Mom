"""Move the R3 roof's Tanki vent grille 20 mm toward the hinges (+Y).

The grille is a field of straight through-cuts in the plain 2.4 mm roof plate.
We fill the old field solid, then cut the identical icon outlines 20 mm back.
20 mm is the most that keeps the top row clear of the right hinge base
(Y 116.88 in the file) with ~1.9 mm to spare.
"""
from shapely.geometry import box as sbox
from meshlib import load, to_manifold, save, box, section_xy, extrude

SRC = "02_R3_corrected_reinforced_top_-_print_ONE.stl"
SHIFT_Y = 20.0
PLATE_Z = (0.0, 2.4)
FIELD = (91.0, 142.0, 44.5, 95.5)          # XY bounds around the existing grille
HINGE_BASE_Y = 116.88

roof_tm = load(SRC)
roof = to_manifold(roof_tm)

# The field must contain nothing but the flat plate, or a plain fill would erase features.
v = roof_tm.vertices
inside = (v[:, 0] > FIELD[0]) & (v[:, 0] < FIELD[1]) & (v[:, 1] > FIELD[2]) & (v[:, 1] < FIELD[3] + SHIFT_Y)
assert set(v[inside, 2].round(3)) <= set(PLATE_Z), "unexpected geometry in vent zone"

field = sbox(FIELD[0], FIELD[2], FIELD[1], FIELD[3])
holes = field.difference(section_xy(roof_tm, 1.2))
hx0, hy0, hx1, hy1 = holes.bounds
assert hy1 + SHIFT_Y < HINGE_BASE_Y - 1.5, "shifted grille would hit the hinge base"

filled = roof + box(FIELD[0], FIELD[1], FIELD[2], FIELD[3], *PLATE_Z)
cutter = extrude(holes, PLATE_Z[0] - 1, PLATE_Z[1] + 1).translate([0, SHIFT_Y, 0])
result = filled - cutter

tm = save(result, "02_R3_top_vents_back_20mm_-_print_ONE.stl")
print(f"grille was Y {hy0:.2f}-{hy1:.2f}, now Y {hy0 + SHIFT_Y:.2f}-{hy1 + SHIFT_Y:.2f}; "
      f"clearance to hinge base {HINGE_BASE_Y - hy1 - SHIFT_Y:.2f} mm")
print(f"icons cut: {len(getattr(holes, 'geoms', [holes]))}, watertight={tm.is_watertight}, bodies={len(tm.split(only_watertight=False))}")
