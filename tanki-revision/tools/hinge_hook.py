"""Replace the roof's four U-seats + glued bearing caps with lift-off hook seats.

Each hook wraps the lid's 6.4 mm pivot from the lower front, round the back and over the
top. Its mouth is a throat between the arm tip and a small bump on the lip, set
SQUEEZE narrower than the pivot and facing EXIT (degrees in the case Y-Z plane:
0 = toward the hinges/rear, 90 = up, 180 = toward the front). Every way out has to push
through that throat, so the pivot clicks in and out; the easiest direction is EXIT.
Up, back, down and straight forward are blocked by much more than SQUEEZE.

    python3 hinge_hook.py [exit_deg]     default 165 = forward and 15 deg up
"""
import sys
import numpy as np
import trimesh
import manifold3d as mf
from meshlib import to_manifold, box, save, OUT

SRC = "02_R3_top_vents_back_20mm_bevel4_open120_-_print_ONE.stl"
EXIT = float(sys.argv[1]) if len(sys.argv) > 1 else 165.0
PIVOT_R, CLEAR, WALL = 3.2, 0.3, 3.0      # 0.3 = Ethan's seat clearance
R_IN, R_OUT = PIVOT_R + CLEAR, PIVOT_R + CLEAR + WALL
SQUEEZE, BUMP_R = 0.25, 0.6               # throat is 6.4 - 0.25 = 6.15 mm
SEATED_GAP = 0.27                         # bump-to-pivot gap when the lid is seated

# roof-file frame: Y = case Y + 2, Z = case Z - 53.8
AY, AZ = 142.884 + 2.0, 70.0 - 53.8
BASE_TOP, BASE_REAR = 5.4, 148.384      # hinge-base top and rear edge
OLD_WALL_BOTTOM = 5.2                    # old rear seat wall hangs past the base edge down to here
SEATS_X = ((30.0, 36.7), (47.3, 54.0), (113.4, 120.1), (130.7, 137.4))


def unit(deg):
    return np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])


def throat():
    """Arm-tip corner T and bump centre B (relative to the pivot axis)."""
    u, e = unit(EXIT), unit(EXIT - 90)     # exit direction, and across the throat toward the arm
    w = PIVOT_R - SQUEEZE / 2               # half-width of the throat
    # push the throat forward of the axis until both T and the bump clear the seated pivot
    m = max(np.sqrt(max(R_IN ** 2 - w ** 2, 0)),
            np.sqrt(max((PIVOT_R + SEATED_GAP + BUMP_R) ** 2 - (w + BUMP_R) ** 2, 0))) + 0.02
    return m * u + w * e, m * u - (w + BUMP_R) * e, m


def yz_prism(points, x0, x1):
    """Prism from (Y, Z) points, swept along X from x0 to x1."""
    cs = mf.CrossSection([np.asarray(points, float)], mf.FillRule.Positive)
    rot = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)
    return cs.extrude(x1 - x0).translate([0, 0, x0]).transform(rot)


def polar(r, deg):
    a = np.radians(deg)
    return (AY + r * np.cos(a), AZ + r * np.sin(a))


def arc_band(r0, r1, a0, a1, n=72):
    """Annular sector from angle a0 to a1 (a1 > a0), as (Y, Z) points."""
    ang = np.linspace(a0, a1, n)
    return [polar(r1, a) for a in ang] + [polar(r0, a) for a in ang[::-1]]


def disc(c, r, n=48):
    return [(c[0] + r * np.cos(t), c[1] + r * np.sin(t)) for t in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def ang(v):
    return np.degrees(np.arctan2(v[1], v[0])) % 360


def hook_profile_parts():
    T, B, m = throat()
    arm_end, lip_start = ang(T), ang(B) + 3.0
    parts = [arc_band(R_IN, R_OUT, lip_start - 360, arm_end)]   # lip -> bottom -> back -> over the top
    # post from the hinge base up into the bottom of the hook
    parts.append([(AY - 2.5, BASE_TOP - 0.2), (BASE_REAR, BASE_TOP - 0.2), (BASE_REAR, AZ - R_IN - 0.6),
                  (AY - 2.5, AZ - R_IN - 0.6)])
    parts.append(disc((AY + B[0], AZ + B[1]), BUMP_R))           # the click bump on the lip
    return parts, (arm_end, lip_start, m)


def build():
    roof = to_manifold(trimesh.load(f"{OUT}/{SRC}"))
    parts, bump_ts = hook_profile_parts()
    for x0, x1 in SEATS_X:
        roof -= box(x0, x1, 139.0, BASE_REAR, BASE_TOP, 20)          # old U-seat above the base
        roof -= box(x0, x1, BASE_REAR, 150.5, OLD_WALL_BOTTOM, 20)  # old rear wall past the base edge
        for p in parts:
            roof += yz_prism(p, x0, x1)
        # keep the pivot's running clearance clear of everything
        roof -= yz_prism(disc((AY, AZ), R_IN, 96), x0 - 0.01, x1 + 0.01)
    return roof, bump_ts


if __name__ == "__main__":
    roof, (arm_end, lip_start, m) = build()
    up = int(round(180 - EXIT))
    tm = save(roof, f"02_R3_top_vents_back_20mm_bevel4_open120_hook{up}_-_print_ONE.stl")
    print(f"exit {EXIT} deg ({up} deg above forward): arm over the top to {arm_end:.1f} deg, lip/bump from "
          f"{lip_start:.1f} deg, throat {2 * PIVOT_R - SQUEEZE:.2f} mm wide, {m:.2f} mm forward of the axis")
    print("watertight", tm.is_watertight, "bodies", len(tm.split(only_watertight=False)), "size", np.round(tm.extents, 2))
