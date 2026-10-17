"""2D lift-out check at one hook: slide the pivot circle out of the roof's Y-Z section in
every direction and report the worst squeeze (how far it has to push into the plastic)."""
import sys
import numpy as np
import trimesh
from shapely.geometry import Point, Polygon

ROOF = sys.argv[1] if len(sys.argv) > 1 else "../revised/02_R3_top_vents_back_20mm_bevel4_open120_hook15_-_print_ONE.stl"
AY, AZ, R = 144.884, 16.2, 3.2
tm = trimesh.load(ROOF)
region = None
for loop in tm.section(plane_origin=[33.35, 0, 0], plane_normal=[1, 0, 0]).discrete:
    p = Polygon(loop[:, 1:]).buffer(0)
    region = p if region is None else region.symmetric_difference(p)
local = region.intersection(Point(AY, AZ).buffer(12))


def squeeze(d, travel=10.0):
    u = np.array([np.cos(np.radians(d)), np.sin(np.radians(d))])
    return max(R - local.exterior.distance(Point(0, 0)) * 0 - local.distance(Point(AY + t * u[0], AZ + t * u[1]))
               if not local.contains(Point(AY + t * u[0], AZ + t * u[1])) else 9.9
               for t in np.arange(0, travel, 0.02))


seated = R - local.distance(Point(AY, AZ))
print(f"seated pivot: closest plastic {-seated:.2f} mm away" if seated < 0 else f"seated pivot OVERLAPS by {seated:.2f} mm")
rows = [(d, squeeze(d)) for d in range(0, 360, 5)]
easiest = min(rows, key=lambda r: r[1])
print(f"easiest way out: {easiest[0]} deg, squeeze {easiest[1]:.2f} mm")
print("directions with squeeze < 0.5 mm:", [(d, round(s, 2)) for d, s in rows if s < 0.5])
for name, d in (("straight up", 90), ("back (stop load)", 0), ("down (weight)", 270), ("straight forward", 180)):
    print(f"  {name:18s} {d:3d} deg: {'blocked' if dict(rows)[d] > 1.5 else f'squeeze {dict(rows)[d]:.2f} mm'}")
