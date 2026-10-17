"""Add 4 mm 45-degree bevels to the Tanki purple case and move the front port opening.

Case frame (Ethan's handoff): X toward the Pi, Y toward the hinges, Z up, outer box
167.4 x 146.88, walls 2.4 thick and 53.8 tall. Each part is edited in its own print
coordinates; the mapping to the case frame is noted per part below.

Bevels: the four vertical corners (floor, walls, roof, lid) and the lid's front, left
and right top edges. The lid's hinge edge stays square so the hinges and their stop
are untouched. Thin parts get material added behind a bevel so the bevel never opens
a hole or loses a glue joint.
"""
import os
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon
from meshlib import load, to_manifold, save, OUT

C = 4.0                       # bevel leg length
W, D, T = 167.4, 146.883789, 2.4  # outer width, outer depth (exact, per handoff), wall thickness
DIAG = C + T * np.sqrt(2)    # inner limit for corner blocks behind a wall bevel


def prism(points, axis, lo, hi):
    """Prism from a 2D polygon swept along `axis` ('x', 'y' or 'z') from lo to hi.

    points are (u, v) pairs: for 'z' u,v = x,y; for 'y' u,v = x,z; for 'x' u,v = y,z.
    """
    cs = mf.CrossSection([np.asarray(Polygon(points).exterior.coords)[:-1]], mf.FillRule.EvenOdd)
    if axis == "z":
        return cs.extrude(hi - lo).translate([0, 0, lo])
    if axis == "y":   # rotate about X: (u, v, w) -> (u, -w, v)
        return cs.extrude(hi - lo).translate([0, 0, -hi]).rotate([90, 0, 0])
    # axis x: cyclic permutation (u, v, w) -> (w, u, v), a proper rotation
    rot = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)
    return cs.extrude(hi - lo).translate([0, 0, lo]).transform(rot)


def corner_cut(cx, cy, sx, sy, leg):
    """Triangle removing the region sx*(u-cx) + sy*(v-cy) < leg near corner (cx, cy).

    sx, sy are +1/-1 pointing from the corner into the part.
    """
    e = 1.0
    return [(cx - sx * e, cy - sy * e), (cx + sx * (leg + e), cy - sy * e), (cx - sx * e, cy + sy * (leg + e))]


def check(m, name):
    tm = save(m, name)
    parts = tm.split(only_watertight=False)
    slivers = [p for p in parts if abs(p.volume) < 1e-3]
    if slivers:   # zero-volume face pairs left where coplanar faces met; drop them
        tm = trimesh.util.concatenate([p for p in parts if abs(p.volume) >= 1e-3])
        tm.export(os.path.join(OUT, name))
        print(f"  {name}: dropped {len(slivers)} zero-volume sliver(s)")
    bodies = len(tm.split(only_watertight=False))
    print(f"  {name}: watertight={tm.is_watertight} bodies={bodies} "
          f"size={np.round(tm.extents, 2).tolist()} vol={tm.volume / 1000:.2f} cm3")
    assert tm.is_watertight and bodies == 1, name
    return tm


def end_walls(name, out, port_shift=0.0, fl_clip=None):
    """Front/rear wall. Print coords: x along the wall, y = depth from OUTER face, z up.

    The front wall is in case coordinates as printed; the rear wall is the same shape
    rotated 180 degrees about Z when installed (its icons read correctly from y=0).
    """
    wall = to_manifold(load(name))
    if port_shift:
        # The USB/Ethernet opening is a plain rectangle through the wall.
        x0, x1, z0, z1 = 97.0, 165.0, 7.0, 35.0
        hole = prism([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], "y", -1, T + 1)
        assert abs((hole ^ wall).volume()) < 1e-6, "port opening is not a plain rectangle"
        fill = prism([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], "y", 0, T)
        wall = (wall + fill) - hole.translate([-port_shift, 0, 0])
    for sx, cx, clip in ((1, 0.0, fl_clip or 4.2), (-1, W, 4.2)):
        wall -= prism(corner_cut(cx, 0.0, sx, 1, C), "z", -1, 55)
        # Block behind the bevel: glues to the side wall's inner face, stays clear of
        # the first vent icon column (which starts 4.3 mm from each end).
        u = lambda d: cx + sx * d
        block = [(u(T), 2.0), (u(clip), 2.0), (u(clip), DIAG - clip), (u(T), DIAG - T)]
        wall += prism(block, "z", 0, 53.8)
    return check(wall, out)


def side_wall(name, out):
    """Side wall. Print coords: x along the wall, y = height, z = thickness, OUTER face z=2.4.

    A 4 mm corner bevel passes 1.6 mm into each end of the side wall's outer edge.
    """
    wall = to_manifold(load(name))
    L = 142.08
    leg = C - T
    for sx, cx in ((1, 0.0), (-1, L)):
        wall -= prism(corner_cut(cx, T, sx, -1, leg), "y", -1, 55)
    return check(wall, out)


def floor(name, out):
    f = to_manifold(load(name))
    for cx, cy, sx, sy in ((0, 0, 1, 1), (W, 0, -1, 1), (0, D, 1, -1), (W, D, -1, -1)):
        f -= prism(corner_cut(cx, cy, sx, sy, C), "z", -1, 4)
    return check(f, out)


def roof(name, out):
    """R3 roof. Print coords = case X, case Y + 2 (2 mm forward lip), Z up from wall tops."""
    r = to_manifold(trimesh.load(name) if os.path.isabs(name) else load(name))
    y0, y1 = 2.0, 2.0 + D        # case front and rear faces in file coordinates
    for cx, cy, sx, sy in ((0, y0, 1, 1), (W, y0, -1, 1), (0, y1, 1, -1), (W, y1, -1, -1)):
        r -= prism(corner_cut(cx, cy, sx, sy, C), "z", -1, 20)
    return check(r, out)


def lid(name, out):
    """7in backplate/lid. Print coords: x = case Y (0 front .. D hinge edge),
    z = W - case X, y = depth below the lid's top face (rims hang down to 25.8)."""
    lid_tm = load(name)
    m = to_manifold(lid_tm)
    LX, LZ = D, W
    REIN = C + 1.2 * np.sqrt(2)  # keep >= 1.2 mm (rim thickness) behind every bevel
    added = None

    def add(piece):
        nonlocal m, added
        new = piece - m
        added = new if added is None else added + new
        m += piece

    # Corner posts behind the two front vertical bevels (front rim meets side rims),
    # stopping 0.3 short of the rim bottom. At the case's front-left corner (z = LZ)
    # the roof's raised screen frame (corner at case 2.5/2.5, top 22.4 below the lid
    # top) sits inside the post's footprint, so the post slims down below that depth.
    FRAME_DEPTH, SLIM = 21.9, 4.7
    for cz, sz in ((0.0, 1), (LZ, -1)):
        tri = lambda leg: [(0, cz), (leg, cz), (0, cz + sz * leg)]
        if cz == LZ:
            add(prism(tri(REIN), "y", 0, FRAME_DEPTH))
            add(prism(tri(SLIM), "y", FRAME_DEPTH, 25.5))
        else:
            add(prism(tri(REIN), "y", 0, 25.5))
    # Strips behind the top-edge bevels along the front, left and right edges.
    add(prism([(0, 0), (REIN, 0), (0, REIN)], "z", 0, LZ))                      # front: (x, y)
    for cz, sz in ((0.0, 1), (LZ, -1)):                                        # left/right: (y, z)
        add(prism([(0, cz), (REIN, cz), (0, cz + sz * REIN)], "x", 0, LX))

    # Vertical corner bevels, all four corners.
    for cx, cz, sx, sz in ((0, 0, 1, 1), (0, LZ, 1, -1), (LX, 0, -1, 1), (LX, LZ, -1, -1)):
        m -= prism(corner_cut(cx, cz, sx, sz, C), "y", -1, 30)
    # Top-edge bevels (front, left, right). The hinge edge stays square.
    m -= prism(corner_cut(0, 0, 1, 1, C), "z", -1, LZ + 1)
    for cz, sz in ((0.0, 1), (LZ, -1)):
        m -= prism([(y, z) for z, y in corner_cut(cz, 0, sz, 1, C)], "x", -1, LX + 1)
    tm = check(m, out)
    print(f"  lid material added behind bevels: {added.volume() / 1000:.2f} cm3")
    return tm, added


if __name__ == "__main__":
    print("writing revised parts to", OUT)
    end_walls("03_Front_Tanki_wall_-_print_ONE.stl", "03_Front_wall_bevel4_port_left3.2_-_print_ONE.stl",
              port_shift=3.2, fl_clip=3.6)
    end_walls("04_Rear_Tanki_wall_-_print_ONE.stl", "04_Rear_wall_bevel4_-_print_ONE.stl")
    side_wall("05_Left_Tanki_wall_-_print_ONE.stl", "05_Left_wall_bevel4_-_print_ONE.stl")
    side_wall("06_Right_Tanki_wall_-_print_ONE.stl", "06_Right_wall_bevel4_-_print_ONE.stl")
    floor("Green_toast_bottom_-_CENTER_original_geometry_-_print_ONE.stl",
          "Green_toast_bottom_bevel4_-_print_ONE.stl")
    roof(os.path.join(OUT, "02_R3_top_vents_back_20mm_-_print_ONE.stl"),
         "02_R3_top_vents_back_20mm_bevel4_-_print_ONE.stl")
    lid("01_Extended_7in_display_backplate_-_print_ONE.stl", "01_7in_lid_bevel4_-_print_ONE.stl")
