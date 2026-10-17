"""Check the hook-seat roof: free swing to the stop, and which directions the lid can lift out."""
import numpy as np
import trimesh
from assemble import assembly, REVISED_PLACEMENT
from meshlib import to_manifold
from hinge_sweep import sweep, lid_at

ROOF = "../revised/02_R3_top_vents_back_20mm_bevel4_open120_hook15_-_print_ONE.stl"
roof_tm = trimesh.load(ROOF); roof_tm.apply_transform(REVISED_PLACEMENT["roof"])
roof = to_manifold(roof_tm)
P = assembly("revised")

a, hit, inter = sweep("revised", roof_override=roof_tm, angles=range(0, 131))
print(f"swing: free from 0 to {a - 1} deg, first contact at {a} deg (Y {np.round(np.array(inter.bounding_box())[[1, 4]], 2)})")

steps = np.arange(0.25, 9.01, 0.25)
for ang in (0, 60, 90, 120):
    lid = to_manifold(lid_at(P["lid"], ang))
    free = []
    for d in range(0, 360, 15):
        u = np.array([0, np.cos(np.radians(d)), np.sin(np.radians(d))])
        vols = [(lid.translate(list(u * s)) ^ roof).volume() for s in steps]
        if max(vols[-4:]) < 1e-3:                 # clear of the roof after 8+ mm of travel
            free.append((d, round(max(vols), 2)))
    print(f"lid at {ang:3d} deg: lifts out only toward {[f'{d} deg (peak overlap {v} mm3)' for d, v in free] or 'none'}")
