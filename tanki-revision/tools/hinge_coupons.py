"""Cut a matching test pair for one hinge: roof hook seats + stop block, and the lid knuckle.

Print both, snap the lid piece in, check the click, the free swing to the 120 deg stop, and
that it lifts out forward-and-up. Both keep their parent part's print orientation (the lid piece lies on its back like the lid).
"""
import numpy as np
import trimesh
from meshlib import to_manifold, box, save, OUT

ROOF = "02_R3_top_vents_back_20mm_bevel4_open120_hook15_-_print_ONE.stl"
LID = "01_7in_lid_bevel4_-_print_ONE.stl"

# Roof file frame: left hinge spans X 26-58 (hooks at 30-36.7 and 47.3-54, stop block between).
roof = to_manifold(trimesh.load(f"{OUT}/{ROOF}")) ^ box(24, 60, 126, 153, -1, 30)
r = save(roof.translate([-24, -126, 0]), "TEST_hinge_hook_roof_coupon_-_print_ONE.stl")

# Lid print frame: x = case Y, z = 167.4 - case X, so the same hinge is z 109.4-141.4.
# The lid file lies on its back; stand it back up (x, y, z)_flat -> (x, z, 167.4 - y) to crop.
upright = to_manifold(trimesh.load(f"{OUT}/{LID}")).translate([0, -167.4, 0]).rotate([-90, 0, 0])
lid = upright ^ box(126, 160, -1, 30, 110.9, 139.9)   # clear of the rear-rim segment ends at 110.4 and 140.4
# lay the coupon on its back too, like the real lid print
l = save(lid.translate([-126, 0, -110.9]).rotate([90, 0, 0]).translate([0, 29.0, 0]), "TEST_hinge_hook_lid_coupon_-_print_ONE.stl")
for name, tm in (("roof coupon", r), ("lid coupon", l)):
    print(f"{name}: size {np.round(tm.extents, 1).tolist()} mm, {tm.volume / 1000 * 1.24:.1f} g solid, "
          f"watertight={tm.is_watertight}, bodies={len(tm.split(only_watertight=False))}")
