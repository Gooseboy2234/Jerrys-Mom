"""XY tolerance matrix, 2D part (python3 + shapely/scipy), working on the Y-Z hook section that
Blender cut (sections.json from b1_section_and_swing.py).

Local frame: u = case Y - 142.884 (toward rear), w = case Z - 70.0 (up), angles 0 = +Y, 90 = +Z.

Tolerance models for the ROOF hook (roof prints flat, so print XY = case X/Y):
  I  "isotropic"  : concave surfaces (the bore) shrink by c, convex features (bump, arm-tip end face)
                    grow by v, independently, in the whole Y-Z plane (round Minkowski offsets).
                    This is the literal brief model and the conservative bound.
  P  "print"      : the slicer view: each 0.20 layer is the section at mid-layer, extruded +-0.1,
                    and every perimeter moves by delta in print XY = case Y only (no Z growth).
LID pivot (prints upright, round in Y-Z): uniform diameter change Du, plus an optional seam blob:
  a ridge of radius RB=0.3 whose crest stands h proud of the pivot at absolute angle psi.
  The blob rotates with the lid: at lid angle theta a seam placed at phi (lid frame, theta=0)
  sits at psi = phi - theta, so over the 0-120 swing it visits psi in [phi-120, phi].
"""
import json, itertools, math, sys, csv
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from scipy.ndimage import distance_transform_edt, map_coordinates

import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument('--clear', type=float); _ap.add_argument('--squeeze', type=float)
_ap.add_argument('--bump_r', type=float); _ap.add_argument('--exit', type=float); _ap.add_argument('--tag', default='')
ARGS = _ap.parse_args()
sys.argv = sys.argv[:1]
sys.path.insert(0, '/home/user/Jerrys-Mom/tanki-revision/tools')
import hinge_hook as HH                      # read-only: design parameters and throat geometry

D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
AY, AZ = 142.884, 70.0
R_IN, R_OUT, BUMP_R = HH.R_IN, HH.R_OUT, HH.BUMP_R
T_, B_, _ = HH.throat()
ARM_END, LIP_START = HH.ang(T_), HH.ang(B_) + 3.0
RB = 0.3                                     # seam-blob ridge radius (about one 0.4 line wide at the base)
WIN = 9.0


def pol(r, deg):
    a = np.radians(deg); return np.array([r * np.cos(a), r * np.sin(a)])


def disc(c, r, n=360):
    return Point(c).buffer(r, quad_segs=n // 4)


def arc_band(r0, r1, a0, a1, n=400):
    ang = np.linspace(a0, a1, n)
    return Polygon([pol(r1, a) for a in ang] + [pol(r0, a) for a in ang[::-1]])


# ---------------- sections from Blender
sec = json.load(open(D + 'sections.json'))


def region(loops):
    reg = None
    for l in loops:
        p = Polygon(np.asarray(l) - [AY, AZ]).buffer(0)
        reg = p if reg is None else reg.symmetric_difference(p)
    return reg


S = {x: region(sec['roof'][x]).intersection(disc((0, 0), WIN)) for x in sec['roof']}
S0 = S['33.35']
LID = {x: region(sec['lid'][x]) for x in sec['lid']}
piv = [g for g in getattr(LID['33.35'], 'geoms', [LID['33.35']]) if g.distance(Point(0, 0)) == 0][0]
pv = np.asarray(piv.exterior.coords)[:-1]
_A = np.c_[2 * pv, np.ones(len(pv))]; _sol = np.linalg.lstsq(_A, (pv ** 2).sum(1), rcond=None)[0]
PIV_C = _sol[:2]; PIV_R = float(np.sqrt(_sol[2] + (PIV_C ** 2).sum()))   # algebraic circle fit
BUMP0 = S0.intersection(disc(B_, BUMP_R + 0.03))


def hh_hook_local():
    """hinge_hook.py's own hook (parts minus bore) in the local frame, for HH's current globals."""
    parts, _ = HH.hook_profile_parts()
    u = unary_union([Polygon(np.asarray(p) - [HH.AY, HH.AZ]).buffer(0) for p in parts])
    return u, disc((0, 0), HH.R_IN)


def use_design(clear=None, squeeze=None, bump_r=None, exit_deg=None):
    """Rebuild the seat section with changed hinge_hook.py parameters (the rest of the roof kept)."""
    global S0, R_IN, R_OUT, BUMP_R, T_, B_, ARM_END, LIP_START, BUMP0
    old_hook, old_bore = hh_hook_local()
    rest = S0.difference(old_hook.buffer(0.01)).difference(disc((0, 0), HH.R_IN + 0.02))
    if clear is not None: HH.CLEAR = clear
    if squeeze is not None: HH.SQUEEZE = squeeze
    if bump_r is not None: HH.BUMP_R = bump_r
    if exit_deg is not None: HH.EXIT = exit_deg
    HH.R_IN = HH.PIVOT_R + HH.CLEAR; HH.R_OUT = HH.R_IN + HH.WALL
    new_hook, new_bore = hh_hook_local()
    S0 = unary_union([rest, new_hook]).buffer(0.012).buffer(-0.012).difference(new_bore).intersection(disc((0, 0), WIN)).buffer(0)
    R_IN, R_OUT, BUMP_R = HH.R_IN, HH.R_OUT, HH.BUMP_R
    T_, B_, _ = HH.throat()
    ARM_END, LIP_START = HH.ang(T_), HH.ang(B_) + 3.0
    BUMP0 = S0.intersection(disc(B_, BUMP_R + 0.03))

# ---------------- tolerance models


def model_I(c, v):
    ext = arc_band(R_IN - 0.45, R_IN + 0.01, LIP_START - 360, ARM_END)
    grown = unary_union([S0, ext]).buffer(v, quad_segs=32) if v else unary_union([S0, ext])
    m = grown.difference(disc((0, 0), R_IN - c))
    bump = BUMP0.buffer(v, quad_segs=32) if v else BUMP0
    return unary_union([m, bump]).intersection(disc((0, 0), WIN)).buffer(0)


def model_P(delta, s0=None, phase=0.0):
    s0 = S0 if s0 is None else s0
    rects = []
    for k in range(0, 200):
        z0 = 53.8 + phase + 0.2 * k - AZ; zm = z0 + 0.1
        if zm < -WIN or zm > WIN: continue
        inter = s0.intersection(LineString([(-WIN - 1, zm), (WIN + 1, zm)]))
        for g in getattr(inter, 'geoms', [inter]):
            if g.is_empty or g.geom_type != 'LineString': continue
            y = np.asarray(g.coords)[:, 0]
            rects.append(box(y.min() - delta, z0 - 1e-6, y.max() + delta, z0 + 0.2 + 1e-6))
    return unary_union(rects).intersection(disc((0, 0), WIN)).buffer(0)


# ---------------- per-profile measurements


def throat_width(M):
    """Largest circle diameter that can escape from the seat: bisection in C-space."""
    far = [pol(r, a) for a in range(0, 360, 5) for r in (8.2,)]

    def escapes(r):
        free = box(-12, -12, 12, 12).difference(M.buffer(r, quad_segs=128))
        comp = [g for g in getattr(free, 'geoms', [free]) if g.contains(Point(0, 0))]
        if not comp: return False
        return any(comp[0].contains(Point(p)) for p in far)

    lo, hi = 2.5, 3.6
    if not escapes(lo): return 2 * lo
    for _ in range(22):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if escapes(mid) else (lo, mid)
    return 2 * lo


def gate_pieces(M):
    arm = M.intersection(Polygon([(0, 0)] + [pol(9, a) for a in np.linspace(60, 150, 30)]))
    lip = M.intersection(Polygon([(0, 0)] + [pol(9, a) for a in np.linspace(185, 265, 30)]))
    return arm, lip


def slide_pen(M, deg, r):
    u = pol(1, deg); best = -9
    for t in np.arange(0, 10, 0.01):
        d = M.distance(Point(t * u))
        if d == 0: return 9.9               # centre would have to pass through solid wall
        best = max(best, r - d)
    return best


GRID = 0.004
gx = np.arange(-4.6, 4.6 + 1e-9, GRID)


def dist_field(M):
    X, Y = np.meshgrid(gx, gx, indexing='ij')
    inside = shapely.contains_xy(M, X.ravel(), Y.ravel()).reshape(X.shape)
    return distance_transform_edt(~inside) * GRID


def field_at(F, pts):
    idx = (pts - gx[0]) / GRID
    return map_coordinates(F, idx.T, order=1, mode='nearest')


def profile_metrics(M):
    W = throat_width(M)
    arm, lip = gate_pieces(M)
    sector = Polygon([(0, 0)] + [pol(9, a) for a in np.linspace(215, 245, 20)])
    bump_d = M.intersection(sector).distance(Point(0, 0))
    pa, pl = shapely.ops.nearest_points(arm, lip)
    gate_dir = math.degrees(math.atan2(pa.y - pl.y, pa.x - pl.x)) % 360     # lip -> arm across the throat
    return dict(W=min(W, arm.distance(lip)), W_cspace=W, W_gate=arm.distance(lip), gate_dir=gate_dir,
                bore_d=M.distance(Point(0, 0)), bump_d=bump_d, F=dist_field(M), M=M)


PSI = np.arange(0, 360, 1.0)
OFF = np.array([(x, y) for x in np.arange(-0.4, 0.4001, 0.01) for y in np.arange(-0.4, 0.4001, 0.01)])


def corner(pm, Du, h):
    M, F = pm['M'], pm['F']
    ru = PIV_R + Du / 2
    clear_c = pm['bore_d'] - ru                                   # centred, no blob (exact)
    bump_gap = pm['bump_d'] - ru
    # blob: disc RB centred at (ru + h - RB) along psi
    if h > 0:
        qs = np.array([pol(ru + h - RB, p) for p in PSI])
        dq = shapely.distance(M, shapely.points(qs)) - RB
        clear_psi = np.minimum(clear_c, dq)
    else:
        clear_psi = np.full(len(PSI), clear_c)
    # best position of the pivot centre (free play lets it dodge): coarse psi for speed
    best_psi = []
    for i in range(0, 360, 5):
        p = PSI[i]
        t1 = field_at(F, OFF) - ru
        if h > 0:
            t2 = field_at(F, OFF + pol(ru + h - RB, p)) - RB
            t1 = np.minimum(t1, t2)
        best_psi.append(t1.max())
    best_psi = np.array(best_psi)
    W = pm['W']
    sq0 = 2 * ru - W
    sqb = 2 * ru + h - W
    # squeeze vs blob direction while the pivot translates through the gate (no rotation then)
    def extra(alpha):
        if h <= 0: return 0.0
        dc = ru + h - RB; s2 = RB ** 2 - (dc * math.sin(math.radians(alpha))) ** 2
        if s2 < 0 or math.cos(math.radians(alpha)) < 0: return 0.0
        return max(0.0, dc * math.cos(math.radians(alpha)) + math.sqrt(s2) - ru)
    g = pm['gate_dir']
    sq_psi = np.array([sq0 + max(extra(p - g), extra(p - g - 180)) for p in PSI])
    hard_psi = [int(p) for p, q in zip(PSI, sq_psi) if q > 0.45]
    # seam angles phi (lid frame) for which the whole 0-120 swing keeps >= 0.05
    bad = clear_psi < 0.05
    ok_phi = [phi for phi in range(360) if not any(bad[int((phi - t) % 360)] for t in range(0, 121))]
    return dict(ru=ru, clear_center=clear_c, clear_swing_min=float(clear_psi.min()),
                worst_psi=float(PSI[int(np.argmin(clear_psi))]), bump_gap=bump_gap,
                best_pos_min=float(best_psi.min()), sq_noblob=sq0, sq_blob=sqb,
                safe_seam_frac=len(ok_phi) / 360.0, safe_seam=ok_phi, hard_click_psi=hard_psi)


def ranges(lst):
    if not lst: return 'none'
    if len(lst) == 360: return 'all'
    s = sorted(lst); out = []; a = b = s[0]
    for x in s[1:]:
        if x == b + 1: b = x
        else: out.append((a, b)); a = b = x
    out.append((a, b))
    if len(out) > 1 and out[0][0] == 0 and out[-1][1] == 359:
        out = [(out[-1][0] - 360, out[0][1])] + out[1:-1]
    return ';'.join(f'{a}..{b}' for a, b in out)


def verdict(r):
    flags = []
    if r['best_pos_min'] < 0: flags.append('JAM')
    elif r['clear_swing_min'] < 0.05: flags.append('BIND')     # fails the 0.05 criterion, may rub/tick
    if r['sq_noblob'] < 0.10: flags.append('NO_CLICK' if r['sq_noblob'] > 0 else 'FALLS_OUT')
    if r['sq_blob'] > 0.45: flags.append('HARD_CLICK')
    if r['clear_center'] > 0.35: flags.append('RATTLE')
    return '+'.join(flags) or 'OK'


if __name__ == '__main__':
    TAG = ARGS.tag
    if ARGS.clear is not None or ARGS.squeeze is not None or ARGS.bump_r is not None or ARGS.exit is not None:
        S_orig = S0
        use_design()                                   # rebuild with UNCHANGED params: must reproduce the STL
        print('rebuild-with-design-params vs Blender section sym-diff area',
              round(S0.symmetric_difference(S_orig).area, 5))
        use_design(ARGS.clear, ARGS.squeeze, ARGS.bump_r, ARGS.exit)
        print(f'PROPOSAL CLEAR={HH.CLEAR} SQUEEZE={HH.SQUEEZE} BUMP_R={HH.BUMP_R} EXIT={HH.EXIT}  tag {TAG}')
    # ---------- harness sanity on the nominal geometry
    print(f'pivot fit from Blender lid section: centre {PIV_C.round(4)} r {PIV_R:.4f}')
    print('sections at X 33.35 vs 50.65 sym-diff area', round(S['33.35'].symmetric_difference(S['50.65']).area, 5))
    pmN = profile_metrics(S0)
    print(f"NOMINAL: bore gap {pmN['bore_d'] - PIV_R:.4f}  bump gap {pmN['bump_d'] - PIV_R:.4f}  "
          f"throat (C-space) {pmN['W_cspace']:.4f}  gate (arm-lip) {pmN['W_gate']:.4f} dir {pmN['gate_dir']:.1f}  squeeze {2 * PIV_R - pmN['W']:.4f}")
    Tc = pol(R_IN, ARM_END)
    print(f"  design throat |T-B|-BUMP_R = {np.hypot(*(T_ - B_)) - BUMP_R:.4f} (T at r {np.hypot(*T_):.3f}); "
          f"actual arm corner on R_IN at the same angle: {np.hypot(*(Tc - B_)) - BUMP_R:.4f}")
    for name, d in (('up', 90), ('back', 0), ('down', 270), ('forward', 180), ('exit', HH.EXIT)):
        print(f'  slide {name:8s} {d:5.0f} deg per-side interference {slide_pen(S0, d, PIV_R):.3f}')
    # model checks: model_I(0,0) == section; model_I(d,d) == section.buffer(d) (outside the clipped window rim)
    core = disc((0, 0), 8.0)
    print('model_I(0,0) vs section sym-diff', round(model_I(0, 0).symmetric_difference(S0).intersection(core).area, 5))
    for d in (0.05, 0.15):
        print(f'model_I({d},{d}) vs section.buffer({d}) sym-diff',
              round(model_I(d, d).symmetric_difference(S0.buffer(d, quad_segs=32)).intersection(core).area, 5))
    pP0 = profile_metrics(model_P(0.0))
    print(f"P model delta 0 (layer stepping only): bore gap {pP0['bore_d'] - PIV_R:.4f} bump gap {pP0['bump_d'] - PIV_R:.4f} "
          f"throat {pP0['W']:.4f} squeeze {2 * PIV_R - pP0['W']:.4f}")

    C = [-0.05, 0.0, 0.05, 0.10, 0.15]
    V = [-0.05, 0.0, 0.05, 0.10, 0.15]
    DU = [-0.05, 0.0, 0.05, 0.10, 0.15, 0.20]
    HB = [0.0, 0.1, 0.2]
    rows = []
    profiles = {}
    for c, v in itertools.product(C, V):
        profiles[('I', c, v)] = profile_metrics(model_I(c, v))
    for d in C:
        profiles[('P', d, d)] = profile_metrics(model_P(d))
    for (mdl, c, v), pm in profiles.items():
        print(f'profile {mdl} c={c:+.2f} v={v:+.2f}: bore r {pm["bore_d"]:.3f} bump d {pm["bump_d"]:.3f} throat {pm["W"]:.3f} '
              f'(gate {pm["W_gate"]:.3f}, cspace {pm["W_cspace"]:.3f})', flush=True)
        for Du, h in itertools.product(DU, HB):
            r = corner(pm, Du, h)
            r.update(model=mdl, c=c, v=v, Du=Du, h=h, in_spec=(Du + h <= 0.2001), W=pm['W'])
            r['verdict'] = verdict(r)
            r['safe_seam_ranges'] = ranges(r.pop('safe_seam'))
            r['hard_click_psi'] = ranges(r.pop('hard_click_psi'))
            rows.append(r)
    keys = ['model', 'c', 'v', 'Du', 'h', 'in_spec', 'ru', 'W', 'clear_center', 'clear_swing_min', 'worst_psi', 'bump_gap',
            'best_pos_min', 'sq_noblob', 'sq_blob', 'safe_seam_frac', 'safe_seam_ranges', 'hard_click_psi', 'verdict']
    with open(D + f'matrix{TAG}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, keys); w.writeheader()
        for r in rows:
            w.writerow({k: (round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in keys})
    # blocked directions at the loosest corner
    Mloose = profiles[('I', -0.05, -0.05)]['M']
    for name, d in (('up', 90), ('back', 0), ('down', 270)):
        print(f'LOOSEST (c=v=-0.05, Du=-0.05) slide {name}: per-side interference {slide_pen(Mloose, d, PIV_R - 0.025):.3f}')
    # profiles for Blender
    json.dump({f'{k[0]}_{k[1]:+.2f}_{k[2]:+.2f}': [list(map(list, np.asarray(g.exterior.coords)))
                                                    for g in getattr(pm['M'], 'geoms', [pm['M']])]
               for k, pm in profiles.items()}, open(D + f'profiles{TAG}.json', 'w'))
    json.dump(dict(PIV_R=PIV_R, PIV_C=list(PIV_C), RB=RB), open(D + f'pivot{TAG}.json', 'w'))
    print('wrote', len(rows), 'rows')
