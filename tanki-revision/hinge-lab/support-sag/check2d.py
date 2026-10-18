"""Independent 2-D cross-check (shapely) of the Blender results, at the seat mid-section X 33.35.

* Section the roof STLs (nominal and the sagged ones Blender exported) in the case Y-Z plane.
* Also re-implement the sag on the nominal 2-D profile (boundary points with overhang angle >= 60 moved
  down SAG, 45..60 moved down DROOP) so the 3-D vertex displacement is checked independently.
* Seated gap = distance(axis, profile) - 3.2.  Bump gap = same, restricted to the 200..250 deg sector.
* Throat (bottleneck) width = 2 * largest disc radius that can escape from the axis to the outside:
  erode the free space by r and test whether the axis stays connected to a far point (bisection on r).
* Support region: vertical columns under every supported boundary segment down to the next solid,
  with 0.2 top and 0.2 bottom Z distance; report how much of it is inside the pivot channel.
usage: python3 check2d.py <out_dir>
"""
import sys, json, glob, os
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LAB = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/'
OUT = sys.argv[1] if len(sys.argv) > 1 else LAB + 'support-sag/out'
AY, AZ, R = 142.884, 70.0, 3.2
X = 33.35


def section(path, x=X):
    m = trimesh.load(path)
    s = m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    polys = []
    for ent in s.discrete:
        pts = np.asarray(ent)[:, 1:3]
        if len(pts) >= 3:
            polys.append(Polygon(pts).buffer(0))
    return unary_union(polys)


def hook_only(g):
    """the piece containing the hook (around the axis)"""
    geoms = list(g.geoms) if hasattr(g, 'geoms') else [g]
    return max(geoms, key=lambda p: p.intersection(Point(AY, AZ).buffer(7)).area)


def ring_points(poly, step=0.02):
    ring = np.asarray(poly.exterior.coords)
    out = []
    for a, b in zip(ring[:-1], ring[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        for t in np.arange(n) / n:
            out.append(a + t * (b - a))
    return np.array(out)


def outward_normals(pts, poly):
    # exterior ring is CCW after orient(); outward normal of segment (dy, -dx)
    t = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return n


def seg_alpha(pts):
    """overhang angle of each boundary segment pts[i] -> pts[i+1] (CCW ring: outward normal = (dy, -dx))"""
    t = np.roll(pts, -1, 0) - pts
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return np.degrees(np.arcsin(np.clip(-n[:, 1], -1, 1))), n


def sag2d(poly, sag, droop, exy=0.0):
    """same rule as the Blender variant: a boundary point takes the largest displacement of its two segments;
    supported (alpha >= 60) moves down SAG, droop (45..60) moves down DROOP; exy = horizontal XY error
    (outward along the sign of the horizontal normal)."""
    from shapely.geometry.polygon import orient
    poly = orient(poly, 1.0)
    pts = ring_points(poly)
    a, n = seg_alpha(pts)
    d = np.where(a >= 60, sag, np.where(a >= 45, droop, 0.0))
    onbed = (pts[:, 1] < 53.81) & (np.roll(pts, -1, 0)[:, 1] < 53.81)
    d[onbed] = 0.0
    dv = np.maximum(d, np.roll(d, 1))
    q = pts.copy(); q[:, 1] -= dv
    if exy:
        ny = (n[:, 0] + np.roll(n[:, 0], 1)) / 2
        q[:, 0] += exy * np.clip(ny / 0.5, -1, 1)
    return Polygon(q).buffer(0), pts, a


def floating_gap(poly):
    """largest pivot-size circle that fits in the (sagged) bore if the pivot is free to settle off the axis:
    Chebyshev centre of bore-disc(3.5) minus the profile; returns (gap, centre offset dy, dz)"""
    from shapely.ops import polylabel
    region = Point(AY, AZ).buffer(3.5 + 1e-3, resolution=256).difference(poly)
    if hasattr(region, 'geoms'):
        region = max(region.geoms, key=lambda g: g.area)
    c = polylabel(region, tolerance=1e-4)
    rr = min(c.distance(poly.exterior), c.distance(Point(AY, AZ).buffer(3.5 + 1e-3, resolution=256).exterior))
    return round(rr - R, 4), round(c.x - AY, 3), round(c.y - AZ, 3)


def free_space(poly):
    return box(AY - 25, AZ - 25, AY + 25, AZ + 25).difference(poly)


def can_escape(free, r):
    er = free.buffer(-r, resolution=64)
    geoms = list(er.geoms) if hasattr(er, 'geoms') else [er]
    far = Point(AY - 20, AZ + 20)
    for g in geoms:
        if g.contains(Point(AY, AZ)):
            return g.contains(far)
    return False


def bottleneck(poly):
    free = free_space(poly)
    lo, hi = 2.0, 3.6
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if can_escape(free, mid) else (lo, mid)
    return 2 * lo


def bump_gap(poly):
    sector = Polygon([(AY, AZ)] + [(AY + 9 * np.cos(np.radians(t)), AZ + 9 * np.sin(np.radians(t)))
                                    for t in np.linspace(200, 250, 40)])
    return Point(AY, AZ).distance(poly.intersection(sector)) - R


def support2d(poly, top=0.2, bot=0.2):
    from shapely.geometry.polygon import orient
    poly = orient(poly, 1.0)
    pts = ring_points(poly, 0.02)
    a, n = seg_alpha(pts)
    cols = []
    for p, al in zip(pts, a):
        if al < 60 or p[1] < 53.81:
            continue
        ray = LineString([(p[0], p[1] - 1e-3), (p[0], 40)])
        hit = ray.intersection(poly.boundary)
        zs = [g.y for g in (hit.geoms if hasattr(hit, 'geoms') else [hit]) if not g.is_empty and g.y < p[1] - 1e-3]
        zb = max(zs) if zs else 53.8
        if p[1] - top > zb + bot:
            cols.append(box(p[0] - 0.011, zb + bot, p[0] + 0.011, p[1] - top))
    return unary_union(cols) if cols else Polygon()


if __name__ == '__main__':
    res = {}
    nom = hook_only(section(LAB + 'roof_left_hinge_case.stl'))
    lidsec = section(LAB + 'lid_left_hinge_case_closed.stl')
    piv = min((list(lidsec.geoms) if hasattr(lidsec, 'geoms') else [lidsec]), key=lambda p: Point(AY, AZ).distance(p.centroid))
    res['lid_pivot_section'] = dict(centroid=[round(piv.centroid.x, 3), round(piv.centroid.y, 3)],
                                    eq_radius=round(float(np.sqrt(piv.area / np.pi)), 4))
    rows = []
    for sag, dr in [(0, 0), (0.1, 0.05), (0.2, 0.1), (0.3, 0.15), (0.3, 0.0), (0.0, 0.15)]:
        p = sag2d(nom, sag, dr)[0] if (sag or dr) else nom
        w = bottleneck(p)
        rows.append(dict(src='2d-resag', sag=sag, droop=dr, floating_gap=floating_gap(p), seated_gap=round(Point(AY, AZ).distance(p) - R, 4),
                         bump_gap=round(bump_gap(p), 4), throat=round(w, 4), squeeze=round(6.4 - w, 4)))
        print(rows[-1], flush=True)
    for f in sorted(glob.glob(OUT + '/roof_sag*.stl')):
        p = hook_only(section(f))
        w = bottleneck(p)
        rows.append(dict(src=os.path.basename(f), seated_gap=round(Point(AY, AZ).distance(p) - R, 4),
                         bump_gap=round(bump_gap(p), 4), throat=round(w, 4), squeeze=round(6.4 - w, 4)))
        print(rows[-1], flush=True)
    res['rows'] = rows
    sup = support2d(nom)
    bore = Point(AY, AZ).buffer(3.5, resolution=128)
    res['support2d'] = dict(area_total=round(sup.area, 3), area_in_bore=round(sup.intersection(bore).area, 3),
                            bounds_in_bore=[round(v, 3) for v in sup.intersection(bore).bounds])
    print(res['support2d'])
    json.dump(res, open(OUT + '/check2d.json', 'w'), indent=1)

    # plot: nominal vs worst sag, support region
    fig, ax = plt.subplots(1, 2, figsize=(13, 6.5))
    worst = sag2d(nom, 0.3, 0.15)[0]
    for k, a_ in enumerate(ax):
        a_.fill(*nom.exterior.xy, color='#c9d3e0', label='roof hook (nominal)')
        a_.plot(*worst.exterior.xy, color='#c0392b', lw=1, label='sag 0.30 / droop 0.15')
        for g in (sup.geoms if hasattr(sup, 'geoms') else [sup]):
            if not g.is_empty:
                a_.fill(*g.exterior.xy, color='#f0b429', alpha=0.6, lw=0)
        a_.plot(*Point(AY, AZ).buffer(R).exterior.xy, color='#2e7d32', lw=1, label='pivot r 3.2')
        a_.set_aspect('equal')
        if k == 1:
            a_.set_xlim(AY - 4.2, AY + 4.2); a_.set_ylim(AZ - 4.2, AZ + 4.2)
        else:
            a_.set_xlim(AY - 9, AY + 9); a_.set_ylim(58, AZ + 8)
        a_.set_xlabel('case Y (mm)'); a_.set_ylabel('case Z (mm)')
    ax[0].fill([], [], color='#f0b429', alpha=0.6, label='support (Bambu 30 deg threshold, 0.2 Z gaps)')
    ax[0].legend(loc='lower left', fontsize=8)
    ax[0].set_title('Hook section X 33.35, roof print orientation (+Z up)')
    ax[1].set_title('Bore close-up')
    plt.tight_layout(); plt.savefig(OUT + '/section_sag_support.png', dpi=130)
    print('WROTE', OUT + '/check2d.json')
