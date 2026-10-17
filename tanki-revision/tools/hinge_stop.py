"""Move the roof's two hinge stop blocks forward so the lid opens further.

The lid's centre knuckle tab hits the back face of a 7.6 x 3.8 x 3.8 mm block on each
hinge base; Ethan's position gives a ~106 deg stop. Sliding the block toward the front
lets the tab swing further before it lands. Past ~125 deg the lid's rear edge reaches the
back of the hinge seats, which are not meant to take that load, so stay below that.
"""
import sys
import numpy as np
import trimesh
from meshlib import to_manifold, to_trimesh, box, save, OUT
from assemble import REVISED_PLACEMENT
from hinge_sweep import sweep

SRC = "02_R3_top_vents_back_20mm_bevel4_-_print_ONE.stl"
BLOCKS_X = ((38.2, 45.8), (121.6, 129.2))
BLOCK_Y, BLOCK_Z = (137.38, 141.15), (5.40, 9.20)    # roof-file coordinates


def roof_with_shift(d):
    m = to_manifold(trimesh.load(f"{OUT}/{SRC}"))
    for x0, x1 in BLOCKS_X:
        m -= box(x0 - 0.01, x1 + 0.01, BLOCK_Y[0] - 0.01, BLOCK_Y[1] + 0.01, BLOCK_Z[0], BLOCK_Z[1] + 0.1)
        # new block overlaps the base by 0.2 mm so the union is solid
        m += box(x0, x1, BLOCK_Y[0] - d, BLOCK_Y[1] - d, BLOCK_Z[0] - 0.2, BLOCK_Z[1])
    return m


def stop_angle(d):
    rt = to_trimesh(roof_with_shift(d)); rt.apply_transform(REVISED_PLACEMENT["roof"])
    a, hit, inter = sweep("revised", roof_override=rt, angles=np.arange(100, 130.01, 0.5))
    contact_y = np.array(inter.bounding_box())[[1, 4]] if inter.volume() > 0 else None
    return a, hit, contact_y


if __name__ == "__main__":
    target = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
    lo, hi = 0.0, 6.0
    for _ in range(9):                      # bisection on the forward shift
        mid = (lo + hi) / 2
        a, _, _ = stop_angle(mid)
        lo, hi = (mid, hi) if a < target else (lo, mid)
    d = round(hi, 2)
    a, hit, cy = stop_angle(d)
    print(f"block shift {d} mm forward -> lid stops at {a} deg on {list(hit)}; contact case Y {np.round(cy, 2)}")
    tm = save(roof_with_shift(d), f"02_R3_top_vents_back_20mm_bevel4_open{int(target)}_-_print_ONE.stl")
    print("watertight", tm.is_watertight, "bodies", len(tm.split(only_watertight=False)))
