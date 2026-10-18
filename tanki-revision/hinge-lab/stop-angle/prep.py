"""Build print-reality meshes (case frame) for the stop-angle test.

Roof prints flat (print Z = case Z - 53.8, 0.20 layers, first layer 0.20): each layer is the
roof's XY section at mid-layer, offset by e_roof (outward on convex, i.e. a 2-D buffer),
extruded over the layer.  The stop block is split out so its Y position / top layer can vary.

Lid prints upright (print Z along case X): each 0.20 layer along X is the lid's YZ section at
mid-layer, offset by e_lid; the pivot discs get their own radius error e_piv.

usage: python3 prep.py <outdir> <e_roof list> <e_lid list> <e_piv list>
writes roof_rest_r{e}.stl, roof_block_r{e}_dy{dy}_top{t}.stl, lid_body_l{e}.stl, lid_pivot_p{e}.stl
and the raw (no slicing, no offset) control versions.
"""
import sys, os, json
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon, box as sbox
from shapely import affinity
from shapely.ops import unary_union

HL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOF = trimesh.load(f"{HL}/roof_left_hinge_case.stl")
LID = trimesh.load(f"{HL}/lid_left_hinge_case_closed.stl")
AY, AZ = 142.884, 70.0
LH, ZOFF = 0.20, 53.8
LID_BED_X = 167.4            # lid print Z = 167.4 - case X (assemble.py placement)


def polys(path2d):
    """Even-odd fill of the closed section loops -> list of shapely polygons."""
    acc = None
    for d in path2d.discrete:
        if len(d) < 3: continue
        g = Polygon(d).buffer(0)
        if g.is_empty: continue
        acc = g if acc is None else acc.symmetric_difference(g)
    if acc is None: return []
    acc = acc.buffer(0)
    gs = acc.geoms if hasattr(acc, "geoms") else [acc]
    return [g for g in gs if g.area > 1e-4]


ROOF_XBREAKS = [24.0, 26.0, 26.3, 26.5, 30.0, 36.7, 38.2, 45.8, 47.3, 53.434, 54.0, 57.5, 57.7, 58.0, 60.0]


def yz_profile(mesh, x):
    s = mesh.section([1, 0, 0], [x, 0, 0])
    T = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x], [0, 0, 0, 1]], float)
    p2, _ = s.to_2D(to_2D=T, check=False)
    return unary_union(polys(p2))


def roof_layers():
    """[(z0, z1, [shapely polys in case XY])], the slicer's mid-layer sections.

    The roof crop's planar X end caps are badly triangulated (folded, zero-volume fins), so XY
    plane sections of the STL are unreliable.  The roof is prismatic along X between the
    breakpoints in ROOF_XBREAKS, so each layer's XY section is rebuilt exactly from YZ
    profiles taken at each segment's mid X: Y-intervals at mid-layer height x segment X range.
    """
    profs = [(a, b, yz_profile(ROOF, (a + b) / 2)) for a, b in zip(ROOF_XBREAKS[:-1], ROOF_XBREAKS[1:])]
    zmax = ROOF.bounds[1, 2] - ZOFF
    res, k = [], 0
    while LH * k + LH / 2 < zmax:
        z0, z1 = LH * k, LH * (k + 1); zm = ZOFF + (z0 + z1) / 2 + 1e-4
        rects = []
        for a, b, pr in profs:
            cut = pr.intersection(sbox(100, zm - 1e-7, 200, zm + 1e-7))
            gs = cut.geoms if hasattr(cut, "geoms") else [cut]
            for g in gs:
                if g.is_empty: continue
                y0, _, y1, _ = g.bounds
                if y1 - y0 > 1e-4: rects.append(sbox(a, y0, b, y1))
        U = unary_union(rects).buffer(0)
        P = list(U.geoms) if hasattr(U, "geoms") else ([U] if not U.is_empty else [])
        res.append((ZOFF + z0, ZOFF + z1, P)); k += 1
    return res


def lid_layers():
    """[(x0, x1, [shapely polys in case (Y, Z)])], layers along case X, mid-layer sections."""
    x_lo, x_hi = LID.bounds[0, 0], LID.bounds[1, 0]
    res = []
    k = 0
    while True:
        p0 = LH * k; p1 = p0 + LH; k += 1                     # print Z of layer
        x1, x0 = LID_BED_X - p0, LID_BED_X - p1
        if x1 <= x_lo: break
        if x0 >= x_hi: continue
        xm = (x0 + x1) / 2 + 1e-4
        if xm <= x_lo or xm >= x_hi: continue
        s = LID.section([1, 0, 0], [xm, 0, 0])
        if s is None: continue
        # map (x, y, z) -> (y, z, x - xm)
        T = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -xm], [0, 0, 0, 1]], float)
        p2, _ = s.to_2D(to_2D=T, check=False)
        res.append((max(x0, x_lo), min(x1, x_hi), polys(p2)))
    return res


def is_block(p):
    x0, y0, x1, y1 = p.bounds
    return x0 > 37.0 and x1 < 47.0 and y1 < 138.5


def is_pivot(p):
    y0, z0, y1, z1 = p.bounds
    c = p.centroid
    return abs(c.x - AY) < 0.3 and abs(c.y - AZ) < 0.3 and p.area < 40.0


def off(p, e):
    if abs(e) < 1e-9: return p
    return p.buffer(e, join_style=2, mitre_limit=5.0)


def extrude(p, h, M):
    """Extrude shapely polygon(s) by h along local Z then apply 4x4 M."""
    ms = []
    geoms = p.geoms if isinstance(p, MultiPolygon) else [p]
    for g in geoms:
        if g.is_empty or g.area < 1e-4: continue
        g = g.simplify(0.002)
        m = trimesh.creation.extrude_polygon(g, h)
        m.apply_transform(M); ms.append(m)
    return ms


def zslab(z0):
    M = np.eye(4); M[2, 3] = z0; return M


def xslab(x0):
    # local (u, v, w) = (Y, Z, X)
    return np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)


def save(ms, path):
    m = trimesh.util.concatenate(ms) if ms else trimesh.Trimesh()
    m.export(path)
    return len(m.faces)


def main():
    out = sys.argv[1]
    e_roofs = [float(v) for v in sys.argv[2].split(',')]
    e_lids = [float(v) for v in sys.argv[3].split(',')]
    e_pivs = [float(v) for v in sys.argv[4].split(',')]
    os.makedirs(out, exist_ok=True)
    RL = roof_layers()
    LL = lid_layers()
    info = {"roof_layers": len(RL), "lid_layers": len(LL)}
    # block layers (for the top-layer variants)
    blk_layers = [(z0, z1, [p for p in P if is_block(p)]) for z0, z1, P in RL]
    blk_layers = [b for b in blk_layers if b[2]]
    info["block_layer_z"] = [round(blk_layers[0][0], 3), round(blk_layers[-1][1], 3)]
    info["block_bounds_xy_top_layer"] = [round(v, 3) for v in unary_union(blk_layers[-1][2]).bounds]
    for er in e_roofs:
        rest = []
        for z0, z1, P in RL:
            for p in P:
                if not is_block(p): rest += extrude(off(p, er), z1 - z0, zslab(z0))
        info[f"roof_rest_r{er:+.3f}"] = save(rest, f"{out}/roof_rest_r{er:+.3f}.stl")
        for dy in (-0.05, 0.0, 0.05):
            for dtop in (-1, 0, 1):          # drop / keep / add one 0.20 layer on top
                L = list(blk_layers)
                if dtop < 0: L = L[:-1]
                if dtop > 0: L = L + [(L[-1][1], L[-1][1] + LH, L[-1][2])]
                ms = []
                for z0, z1, P in L:
                    for p in P: ms += extrude(affinity.translate(off(p, er), 0, dy), z1 - z0, zslab(z0))
                save(ms, f"{out}/roof_block_r{er:+.3f}_dy{dy:+.2f}_top{dtop:+d}.stl")
    for el in e_lids:
        body = []
        for x0, x1, P in LL:
            for p in P:
                if not is_pivot(p): body += extrude(off(p, el), x1 - x0, xslab(x0))
        info[f"lid_body_l{el:+.3f}"] = save(body, f"{out}/lid_body_l{el:+.3f}.stl")
    for ep in e_pivs:
        piv = []
        for x0, x1, P in LL:
            for p in P:
                if is_pivot(p): piv += extrude(off(p, ep), x1 - x0, xslab(x0))
        info[f"lid_pivot_p{ep:+.3f}"] = save(piv, f"{out}/lid_pivot_p{ep:+.3f}.stl")
    # pivot X extents and radius for reference
    pv = [(x0, x1, p) for x0, x1, P in LL for p in P if is_pivot(p)]
    info["pivot_x"] = [round(min(a for a, _, _ in pv), 2), round(max(b for _, b, _ in pv), 2)]
    info["pivot_r_nominal_section"] = round(float(np.sqrt(pv[0][2].area / np.pi)), 4)
    json.dump(info, open(f"{out}/prep_info.json", "w"), indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
