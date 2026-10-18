"""2-D metrics of the roof-hook YZ profile (nominal smooth vs layer-sliced + print tolerances).
Inputs come from Blender: out/layers.json (per-layer sections, slice_roof.py) and out/blender_checks.json
(YZ sections of the nominal and sliced STLs, blender_checks.py).
usage: python3 analyze.py [outdir]
"""
import json, sys, math, itertools
import numpy as np
from shapely.geometry import Polygon, LineString, box, Point, MultiPolygon
from shapely.ops import unary_union, polygonize
from shapely import affinity

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
AY, AZ, ZOFF = 142.884, 70.0, 53.8
R_P, R_IN, R_OUT = 3.2, 3.5, 6.5
CLOSE = 0.049
WIN = box(AY - 10, AZ - 10, AY + 10, AZ + 10)

# ---------------- profiles ----------------
def poly_from_segments(segs):
    lines = [LineString(s) for s in segs if s[0] != s[1]]
    polys = list(polygonize(unary_union(lines)))
    g = Polygon()
    for p in polys:               # even-odd
        g = g.symmetric_difference(p)
    return g.buffer(0)

def layer_polys(layers):
    out = []
    for L in layers:
        g = Polygon()
        for lp in L['loops']:
            if len(lp) < 3: continue
            p = Polygon(lp)
            if not p.is_valid: p = p.buffer(0)
            g = g.symmetric_difference(p)
        out.append((L['z0'], L['z1'], g.buffer(0)))
    return out

def sliced_profile(lpolys, x, e=0.0, arachne=False):
    """stepped YZ profile at X=x; e = XY per-surface offset (material grows by e)."""
    rects = []
    ln = LineString([(x, AY - 12), (x, AY + 12)])
    for z0, z1, g in lpolys:
        zc0, zc1 = z0 + ZOFF, z1 + ZOFF
        if zc1 < AZ - 10 or zc0 > AZ + 10: continue
        gg = g.buffer(CLOSE).buffer(-CLOSE)            # slicer slice_closing_radius 0.049
        gg = gg.buffer(e, join_style=2, mitre_limit=5) if e else gg
        s = gg.intersection(ln)
        for seg in getattr(s, 'geoms', [s]):
            if seg.is_empty or seg.geom_type != 'LineString': continue
            ys = [c[1] for c in seg.coords]; y0, y1 = min(ys), max(ys)
            if arachne:                       # Bambu Arachne defaults: min_feature 0.1, min_bead 0.34
                w = y1 - y0
                if w < 0.10: continue
                if w < 0.34: m = (y0 + y1) / 2; y0, y1 = m - 0.17, m + 0.17
            rects.append(box(y0, zc0, y1, zc1))
    return unary_union(rects).buffer(1e-6).buffer(-1e-6).intersection(WIN)

def wedge(a0, a1, r=R_OUT + 0.5):
    pts = [(AY, AZ)] + [(AY + r * math.cos(math.radians(a)), AZ + r * math.sin(math.radians(a)))
                        for a in np.linspace(a0, a1, 40)]
    return Polygon(pts)

def add_sag(P, s_sup, s_droop):
    """support-side sag of the downward-facing seat ceiling: material moves DOWN into the hole.
    Bambu threshold 30 deg -> ceiling within 60..120 deg is on supports; 30..60/120..150 unsupported."""
    extra = []
    if s_sup:   extra.append(affinity.translate(P, 0, -s_sup).intersection(wedge(60, 120)))
    if s_droop: extra.append(affinity.translate(P, 0, -s_droop).intersection(
        unary_union([wedge(30, 60), wedge(120, 150)])))
    return unary_union([P] + extra) if extra else P

# ---------------- metrics ----------------
def boundary_pts(P, step=0.004, rmax=R_OUT + R_P + 0.2):
    pts = []
    geoms = getattr(P, 'geoms', [P])
    for g in geoms:
        for ring in [g.exterior] + list(g.interiors):
            L = ring.length; n = max(int(L / step), 4)
            c = np.array([ring.interpolate(t).coords[0] for t in np.linspace(0, L, n, endpoint=False)])
            pts.append(c)
    p = np.vstack(pts) - [AY, AZ]
    return p[np.hypot(p[:, 0], p[:, 1]) < rmax]

def clearance_profile(p, r):
    d = np.hypot(p[:, 0], p[:, 1]); a = np.degrees(np.arctan2(p[:, 1], p[:, 0])) % 360
    bins = np.full(360, np.inf)
    np.minimum.at(bins, a.astype(int) % 360, d - r)
    return bins, float((d - r).min()), float(a[np.argmin(d)])

def interference(p, r, phi):
    """straight-line lift-out along phi: total (both sides) penetration the pivot must force."""
    u = np.array([math.cos(math.radians(phi)), math.sin(math.radians(phi))])
    e = np.array([math.cos(math.radians(phi - 90)), math.sin(math.radians(phi - 90))])
    t = p @ u; s = p @ e
    ahead = (t >= 0) & (np.abs(s) < r)
    behind = (t < 0) & (np.hypot(p[:, 0], p[:, 1]) < r)      # inside the seated disc
    sl = s[ahead & (s >= 0)]; sr = s[ahead & (s < 0)]
    pl = r - sl.min() if sl.size else 0.0
    pr = r + sr.max() if sr.size else 0.0
    pb = (r - np.hypot(p[behind, 0], p[behind, 1])).max() if behind.any() else 0.0
    return min(2 * r, pl + pr + pb)

def ray_agreement(P, rays):
    """compare Blender ray-cast radial gaps (0.5 deg steps) with the same rays on the 2-D profile"""
    B = P.boundary; d = []
    for k, g in enumerate(rays):
        th = math.radians(k * 0.5)
        it = LineString([(AY, AZ), (AY + 12 * math.cos(th), AZ + 12 * math.sin(th))]).intersection(B)
        if it.is_empty or g is None: continue
        d.append(min(Point(AY, AZ).distance(q) for q in getattr(it, 'geoms', [it])) - R_P - g)
    d = np.abs(np.array(d))
    return {'rays': int(d.size), 'within_0.01': int((d <= 0.01).sum()), 'max_dev': round(float(d.max()), 4),
            'median_dev': round(float(np.median(d)), 5)}

PHIS = np.arange(0, 360, 0.5)
def metrics(P, r_clear, r_click):
    p = boundary_pts(P)
    bins, cmin, camin = clearance_profile(p, r_clear)
    itf = np.array([interference(p, r_click, f) for f in PHIS])
    i0 = int(np.argmin(itf))
    def win(th):
        sel = PHIS[itf <= th]
        if not sel.size: return None
        return [float(sel.min()), float(sel.max()), float(len(sel) * 0.5)]
    seat = np.r_[bins[0:100], bins[240:360]]           # plain seat wall (away from throat)
    return {
        'clear_min': round(cmin, 3), 'clear_min_angle': round(camin, 1),
        'clear_seat_wall_min': round(float(seat.min()), 3), 'clear_seat_wall_max': round(float(seat[np.isfinite(seat)].max()), 3),
        'min_itf_up_60_120': round(float(itf[(PHIS >= 60) & (PHIS <= 120)].min()), 3),
        'min_itf_back_330_30': round(float(itf[(PHIS >= 330) | (PHIS <= 30)].min()), 3),
        'min_itf_down_240_300': round(float(itf[(PHIS >= 240) & (PHIS <= 300)].min()), 3),
        'clear_bump_zone_min': round(float(bins[215:240].min()), 3),
        'clear_bins': [round(float(b), 3) if np.isfinite(b) else None for b in bins],
        'click_squeeze': round(float(itf[i0]), 3), 'click_dir': float(PHIS[i0]),
        'squeeze_at_165': round(float(itf[PHIS == 165.0][0]), 3),
        'block_back_0': round(float(itf[PHIS == 0][0]), 3), 'block_up_90': round(float(itf[PHIS == 90][0]), 3),
        'block_down_270': round(float(itf[PHIS == 270][0]), 3), 'block_fwd_180': round(float(itf[PHIS == 180][0]), 3),
        'window_le_0.45': win(0.45), 'window_lt_0.5': win(0.4999), 'window_lt_0.10': win(0.0999),
        'itf': [round(float(v), 3) for v in itf],
    }

def brief(name, m):
    return (f"{name:<44s} clr min {m['clear_min']:6.3f}@{m['clear_min_angle']:5.1f}  wall {m['clear_seat_wall_min']:.3f}-{m['clear_seat_wall_max']:.3f}"
            f"  bump {m['clear_bump_zone_min']:.3f} | click {m['click_squeeze']:.3f}@{m['click_dir']:.1f} (165:{m['squeeze_at_165']:.3f})"
            f" | back {m['block_back_0']:.2f} up {m['block_up_90']:.2f} down {m['block_down_270']:.2f} fwd {m['block_fwd_180']:.2f}"
            f" | sector-min up {m['min_itf_up_60_120']:.2f} back {m['min_itf_back_330_30']:.2f} down {m['min_itf_down_240_300']:.2f}"
            f" | win<=.45 {m['window_le_0.45']}  <.10 {m['window_lt_0.10']}")

if __name__ == '__main__':
    BL = json.load(open(f'{OUT}/blender_checks.json'))
    LP = layer_polys(json.load(open(f'{OUT}/layers.json'))['layers'])
    res = {}
    # 1. harness check: nominal STL section (Blender) and sliced-STL section vs layer rebuild
    for x in ('33.35', '50.65', '30.5', '53.6'):
        Pn = poly_from_segments(BL['nominal']['sections'][x]).intersection(WIN)
        Pl = sliced_profile(LP, float(x))
        res[f'nominal_x{x}'] = mn = metrics(Pn, R_P, R_P)
        res[f'sliced_x{x}'] = ms = metrics(Pl, R_P, R_P)
        print(brief(f'NOMINAL x={x}', mn)); print(brief(f'SLICED  x={x}', ms))
        if x in BL['sliced']['clearance']['rays']:
            for nm, P in (('sliced', Pl), ('nominal', Pn)):
                agree = ray_agreement(P, BL[nm]['clearance']['rays'][x])
                res[f'ray_agreement_{nm}_x{x}'] = agree
                print(f'   Blender BVH ray-cast vs 2-D {nm} profile: {agree}')
    # 2. tolerance corners on the sliced profile (seat 1 centre; seats are identical prisms)
    X = 33.35
    E = {'xy-0.05': -0.05, 'xy0': 0.0, 'xy+0.15': 0.15}
    PIV = {'d-0.05': (3.175, 3.175), 'd0': (3.2, 3.2), 'd+0.20': (3.3, 3.3), 'blob+0.2': (3.4, 3.3)}  # (local r for clearance, effective r for click: diametral +0.2)
    # ceiling sag: none | no supports in the seat (bridge+overhang droop up to 0.15 over 30..150 deg) |
    # supports in the seat (top Z gap 0.2): 0.10 or 0.30 sag over 60..120, 0.15 droop over 30..60
    SAG = {'sag0': (0, 0), 'nosup.15': (0.15, 0.15), 'sup.10': (0.10, 0.15), 'sup.30': (0.30, 0.15)}
    corners = {}
    for (en, e), (sn, (ss, sd)), arach in itertools.product(E.items(), SAG.items(), (False, True)):
        P = add_sag(sliced_profile(LP, X, e, arach), ss, sd)
        for pn, (rc, rk) in PIV.items():
            key = f'{en}|{pn}|{sn}|{"arachne" if arach else "geom"}'
            m = metrics(P, rc, rk); m.pop('itf'); m.pop('clear_bins')
            corners[key] = m
    res['corners'] = corners
    # same corners on the NOMINAL smooth profile, for comparison (XY offset as a 2-D buffer of the profile)
    Pn = poly_from_segments(BL['nominal']['sections']['33.35']).intersection(WIN)
    ncorners = {}
    for (en, e), (sn, (ss, sd)) in itertools.product(E.items(), SAG.items()):
        P = add_sag(Pn.buffer(e, join_style=2, mitre_limit=5) if e else Pn, ss, sd)
        for pn, (rc, rk) in PIV.items():
            m = metrics(P, rc, rk); m.pop('itf'); m.pop('clear_bins')
            ncorners[f'{en}|{pn}|{sn}'] = m
    res['nominal_corners'] = ncorners
    json.dump(res, open(f'{OUT}/metrics.json', 'w'), indent=0)
    print('\nCORNERS (sliced, x=33.35)  key = xy | pivot | sag | thin-feature model')
    for k, m in corners.items():
        if '|d0|' in k or 'd-0.05' in k or 'blob' in k or 'd+0.20' in k:
            print(brief(k, {**m, 'itf': None}))
