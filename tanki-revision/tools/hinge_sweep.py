"""Rotate the lid about its pivot axis and report where it first collides with the roof."""
import sys
import numpy as np
import trimesh
from assemble import assembly
from meshlib import to_manifold

AXIS_Y, AXIS_Z = 142.884, 70.0


def lid_at(lid, deg):
    """Lid opened by `deg` degrees (front edge rises)."""
    T = trimesh.transformations.rotation_matrix(np.radians(-deg), [1, 0, 0], [0, AXIS_Y, AXIS_Z])
    m = lid.copy(); m.apply_transform(T)
    return m


def sweep(which="revised", lid_override=None, roof_override=None, angles=range(0, 181, 1)):
    P = assembly(which)
    lid = lid_override if lid_override is not None else P["lid"]
    roof = to_manifold(roof_override if roof_override is not None else P["roof"])
    others = {k: to_manifold(P[k]) for k in ("front", "rear", "left", "right", "floor")}
    first = None
    for a in angles:
        lm = to_manifold(lid_at(lid, a))
        hits = {"roof": (lm ^ roof).volume()}
        hits.update({k: (lm ^ m).volume() for k, m in others.items()})
        hit = {k: v for k, v in hits.items() if v > 0.01}
        if hit and first is None:
            first = (a, hit, lm ^ roof)
            break
    return first


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "revised"
    a, hit, inter = sweep(which)
    print(f"{which}: lid first touches at {a} deg: {{{', '.join(f'{k}: {v:.2f} mm3' for k, v in hit.items())}}}")
    if inter.volume() > 0:
        bb = np.round(inter.bounding_box(), 2)
        print("  contact region (case X0,Y0,Z0,X1,Y1,Z1):", bb.tolist())
