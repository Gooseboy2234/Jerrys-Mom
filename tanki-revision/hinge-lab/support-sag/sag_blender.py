"""SUPPORT SAG / OVERHANG DROOP test of the lift-off hook hinge, Blender 4.2 headless (case frame, mm).

Roof print orientation: print Z = case Z - 53.8 (roof underside on the bed), so "down" in print = case -Z.
 1. Classify every roof face by its overhang angle  alpha = asin(-n_z)  (0 = vertical wall, 90 = ceiling):
      supported  alpha >= 60  (Bambu default support threshold 30 deg from horizontal -> printed onto support)
      droop      45 <= alpha < 60  (unsupported steep-ish overhang)
      mild       0 < alpha < 45   (prints fine, not displaced)
    faces lying on the bed (Z = 53.8) are excluded.
 2. Make variants: vertices of supported faces move DOWN by SAG, of droop faces DOWN by DROOP
    (a vertex takes the largest displacement of its faces; conservative). Optional roof XY error E moves each
    vertex horizontally outward by E along the sign of its faces' horizontal normal (holes shrink, bosses grow).
 3. For every variant measure (BVH, Blender):
      - seated radial gap: nearest roof surface to the pivot axis over the seat X range, and the radial
        free radius R(phi) by ray casting from the axis (360 deg);  gap = R - 3.2
      - throat: the pivot centre is pushed out along straight lines at directions 120..210 deg; the channel
        half-width along a line is the min distance from the moving centre to the roof; best line = throat.
        squeeze = pivot diameter - 2*max_line(min distance).  Seated bump gap.
      - blocking: same straight push straight up (90), back (0) and down (270): interference = r - min dist
      - full lid swing 0..130 deg (lid rotated -theta about +X through the axis): signed min clearance of
        sampled lid surface vs roof and roof vs lid, first-contact (stop) angle, and with the stop block
        removed, the secondary-contact angle.
      - support: rays cast straight down from sampled points on supported faces -> where support stands,
        its height, whether it is inside the pivot channel, and +/-X rays from it (removal path).
usage: blender -b --factory-startup --python sag_blender.py -- <out_dir>
"""
import bpy, bmesh, sys, json, math, random, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

LAB = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/'
OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else LAB + 'support-sag/out'
os.makedirs(OUT, exist_ok=True)
AY, AZ, R = 142.884, 70.0, 3.2
BED_Z = 53.8
SEATS = [(30.0, 36.7), (47.3, 54.0)]
SEAT_MID = [33.35, 50.65]
BLOCK_X = (38.2, 45.8)
EXIT = 165.0
random.seed(1)


def load_bm(p):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=p)
    me = bpy.context.scene.objects[0].data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    bm.normal_update()
    return bm


def alpha(f):
    nz = f.normal.z
    return math.degrees(math.asin(max(-1.0, min(1.0, -nz)))) if nz < 0 else 0.0


def on_bed(f):
    return all(v.co.z < BED_Z + 1e-3 for v in f.verts)


HINGE_REGIONS = [(24.0, 60.0), (107.4, 143.4)]


def classify(bm, region=False):
    cls = {}
    for f in bm.faces:
        if on_bed(f) or f.normal.z >= -1e-6:
            continue
        if region:
            c = f.calc_center_median()
            if not (c.y > 130 and any(x0 <= c.x <= x1 for x0, x1 in HINGE_REGIONS)):
                continue
        a = alpha(f)
        cls[f.index] = 'supported' if a >= 60 else ('droop' if a >= 45 else 'mild')
    return cls


def polar(co):
    return math.degrees(math.atan2(co.z - AZ, co.y - AY)) % 360, math.hypot(co.y - AY, co.z - AZ)


def describe(bm, cls):
    """connected groups of down-facing faces per class with location info"""
    groups = []
    seen = set()
    for f in bm.faces:
        if f.index not in cls or f.index in seen:
            continue
        c = cls[f.index]; stack = [f]; comp = []
        seen.add(f.index)
        while stack:
            g = stack.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen and cls.get(h.index) == c:
                        seen.add(h.index); stack.append(h)
        area = sum(g.calc_area() for g in comp)
        vs = [v.co for g in comp for v in g.verts]
        xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
        ctr = [g.calc_center_median() for g in comp]
        ph = [polar(p) for p in ctr]
        al = [alpha(g) for g in comp]
        groups.append(dict(cls=c, faces=len(comp), area=round(area, 3),
                           x=[round(min(xs), 2), round(max(xs), 2)], y=[round(min(ys), 2), round(max(ys), 2)],
                           z=[round(min(zs), 2), round(max(zs), 2)],
                           phi=[round(min(p[0] for p in ph), 1), round(max(p[0] for p in ph), 1)],
                           r=[round(min(p[1] for p in ph), 2), round(max(p[1] for p in ph), 2)],
                           alpha=[round(min(al), 1), round(max(al), 1)]))
    groups.sort(key=lambda g: (-g['area']))
    return groups


def make_variant(base, cls, sag, droop, exy=0.0):
    bm = base.copy()
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    disp = {}
    for f in base.faces:
        c = cls.get(f.index)
        d = sag if c == 'supported' else (droop if c == 'droop' else 0.0)
        if d:
            for v in f.verts:
                disp[v.index] = max(disp.get(v.index, 0.0), d)
    moves = {}
    if exy:
        for v in base.verts:
            nx = sum(f.normal.x * f.calc_area() for f in v.link_faces if abs(f.normal.x) > 0.5)
            ny = [f.normal.y for f in v.link_faces if abs(f.normal.x) < 0.5 and not on_bed(f)]
            dx = 0.0   # axial (X) growth of the seat ends is the XY-tolerance tester's job; only the profile (Y) here
            my = sum(ny) / len(ny) if ny else 0.0
            dy = exy * max(-1.0, min(1.0, my / 0.5))   # full XY offset on walls, tapered on near-horizontal faces (no folds)
            moves[v.index] = (dx, dy)
    for v in bm.verts:
        dz = -disp.get(v.index, 0.0)
        dx, dy = moves.get(v.index, (0.0, 0.0))
        v.co = Vector((v.co.x + dx, v.co.y + dy, v.co.z + dz))
    bm.normal_update()
    return bm


SKEWS = [Vector(d).normalized() for d in ((0.137, 0.513, 0.847), (0.301, -0.201, 0.932), (-0.233, 0.611, -0.757))]


def _parity(tree, p, d, maxd):
    n, q = 0, p.copy()
    for _ in range(200):
        h = tree.ray_cast(q, d, maxd)
        if h[0] is None:
            break
        if h[3] > 2e-4:            # a second hit at the same spot = ray through a shared edge: count once
            n += 1
        q = h[0] + d * 1e-4
    return n % 2


def inside(tree, p, maxd=300.0):
    """ray-parity inside test against a closed mesh, majority of three skewed rays"""
    return sum(_parity(tree, p, d, maxd) for d in SKEWS) >= 2


def signed_nearest(tree, p, maxd=20.0, sign_below=None):
    h = tree.find_nearest(p, maxd)
    if h[0] is None:
        return maxd, None, None
    d = h[3]
    if sign_below is None or d < sign_below:
        if inside(tree, p):
            d = -d
    return d, h[0], h[2]


def seated(tree):
    best = (1e9, None)
    for x0, x1 in SEATS:
        for i in range(0, 61):
            x = x0 + 0.2 + (x1 - x0 - 0.4) * i / 60
            d, p, _ = signed_nearest(tree, Vector((x, AY, AZ)))
            if d < best[0]:
                best = (d, p)
    p = best[1]
    rays = {}
    for x in SEAT_MID:
        g = []
        for k in range(360):
            th = math.radians(k)
            h = tree.ray_cast(Vector((x, AY, AZ)), Vector((0, math.cos(th), math.sin(th))), 15.0)
            g.append(round(h[3], 4) if h[0] is not None else None)
        rays[str(x)] = g
    return dict(min_r=round(best[0], 4), gap=round(best[0] - R, 4),
                at_phi=round(polar(p)[0], 1) if p else None, rays=rays)


def push(tree, deg, smax=6.0, ds=0.01, x=None):
    """min over the straight path of the (signed) distance from the moving pivot centre to the roof"""
    out = []
    for xm in ([x] if x else SEAT_MID):
        u = Vector((0, math.cos(math.radians(deg)), math.sin(math.radians(deg))))
        mind, at = 1e9, 0.0
        n = int(smax / ds)
        for i in range(n + 1):
            s = i * ds
            d, _, _ = signed_nearest(tree, Vector((xm, AY, AZ)) + s * u)
            if d < mind:
                mind, at = d, s
        out.append((mind, at))
    return min(out)


def throat(bm, tree):
    """mouth width = min distance between the arm-tip side (phi 30..118) and the lip/bump side
    (phi 192..268) of the hook profile, both at the seat mid sections (prism -> 2-D distance)."""
    arm, lip = [], []
    for f in bm.faces:
        if abs(f.normal.x) > 0.5:
            continue
        c = f.calc_center_median()
        if not any(x0 <= c.x <= x1 for x0, x1 in SEATS):
            continue
        ph, rr = polar(c)
        if not (3.0 < rr < 7.0):
            continue
        if 30 <= ph <= 118:
            arm.append(f)
        elif 192 <= ph <= 268:
            lip.append(f)
    def tree_of(fs):
        vs, idx, fl = [], {}, []
        for f in fs:
            ids = []
            for v in f.verts:
                if v.index not in idx:
                    idx[v.index] = len(vs); vs.append(v.co.copy())
                ids.append(idx[v.index])
            fl.append(ids)
        return BVHTree.FromPolygons(vs, fl), vs
    t_lip, _ = tree_of(lip)
    best = (1e9, None, None)
    for xm in SEAT_MID:
        # dense points along the arm-side profile edges at x = xm
        for f in arm:
            vs = [v.co for v in f.verts]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                p, q = vs[a], vs[b]
                if abs(p.x - q.x) > 1e-6:
                    continue
                for k in range(21):
                    pt = p + (q - p) * (k / 20)
                    pt = Vector((xm, pt.y, pt.z))
                    h = t_lip.find_nearest(pt, 10.0)
                    if h[0] is not None and h[3] < best[0]:
                        best = (h[3], pt.copy(), h[0].copy())
    d, pa, pl = best
    push165 = push(tree, EXIT, ds=0.01)
    return dict(width=round(d, 4), arm_pt=[round(pa.y, 3), round(pa.z, 3)], arm_phi=round(polar(pa)[0], 1),
                lip_pt=[round(pl.y, 3), round(pl.z, 3)], lip_phi=round(polar(pl)[0], 1),
                dir=round(math.degrees(math.atan2(pl.z - pa.z, pl.y - pa.y)) % 360, 1),
                width_straight165=round(2 * push165[0], 4), at_s_165=round(push165[1], 2))


def bump_gap(tree):
    """seated gap between pivot (r 3.2) and roof surface in the lip/bump sector 200..250 deg"""
    g = 1e9
    for x in SEAT_MID:
        for k in np.arange(200, 250.01, 0.25):
            th = math.radians(k)
            h = tree.ray_cast(Vector((x, AY, AZ)), Vector((0, math.cos(th), math.sin(th))), 15.0)
            if h[0] is not None:
                g = min(g, h[3] - R)
    return round(g, 4)


def blocking(tree, r=R):
    res = {}
    for name, deg in (('up', 90.0), ('back', 0.0), ('down', 270.0), ('forward', 180.0)):
        m, s = push(tree, deg, smax=8.0, ds=0.02)
        res[name] = round(min(r - m, 2 * r), 3)   # interference depth along the straight push, capped at the diameter
    return res


# ---------------------------------------------------------------- swing
PIVOT_X = [(30.2, 37.0), (47.0, 53.8)]   # lid pivot cylinders (from the lid STL X levels)


def lid_pivot_faces(lid):
    """lid faces on the two pivot cylinders (closed state)"""
    out = set()
    for f in lid.faces:
        c = f.calc_center_median()
        rr = math.hypot(c.y - AY, c.z - AZ)
        if abs(f.normal.x) < 0.5 and abs(rr - R) < 0.08:
            out.add(f.index)
        elif abs(f.normal.x) > 0.9 and all(math.hypot(v.co.y - AY, v.co.z - AZ) <= R + 0.02 for v in f.verts):
            out.add(f.index)   # pivot end caps
    return out


def sample_surface(bm, density, keep):
    """points on the surface; returns (point, face_index, axial) with axial = face normal along X"""
    pts = []
    for f in bm.faces:
        vs = [v.co.copy() for v in f.verts]
        ax = abs(f.normal.x) > 0.9
        cand = list(vs)
        n = int(f.calc_area() * density)
        for _ in range(n):
            r1, r2 = random.random(), random.random()
            if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
            cand.append(vs[0] + r1 * (vs[1] - vs[0]) + r2 * (vs[2] - vs[0]))
        for p in cand:
            if keep(p):
                pts.append((p, f.index, ax))
    return pts


def rot(theta):
    T = Matrix.Translation(Vector((0, AY, AZ)))
    return T @ Matrix.Rotation(-math.radians(theta), 4, 'X') @ T.inverted()


def lid_tree(lid, M):
    vs = [M @ v.co for v in lid.verts]
    return BVHTree.FromPolygons(vs, [[v.index for v in f.verts] for f in lid.faces])


def contacts(t_roof, tl, piv):
    pairs = t_roof.overlap(tl)
    p_piv = [q for q in pairs if q[1] in piv]
    p_oth = [q for q in pairs if q[1] not in piv]
    return p_piv, p_oth


def swing(roof, lid, angles, lid_pts, roof_pts, piv):
    """signed clearances over the swing. Axial (X-normal) faces are skipped so the numbers are the radial /
    vertical gaps that sag acts on. 'pivot' = lid pivot cylinder vs roof; 'other' = rest of the lid."""
    t_roof = BVHTree.FromBMesh(roof)
    res = []
    for th in angles:
        M = rot(th)
        tl = lid_tree(lid, M)
        piv_min, oth_min, oth_at = 9.0, 9.0, None
        for p, fi, ax in lid_pts:
            if ax:
                continue
            d, h, _ = signed_nearest(t_roof, M @ p, 3.0, sign_below=0.25)
            if fi in piv:
                piv_min = min(piv_min, d)
            elif d < oth_min:
                oth_min, oth_at = d, h
        for p, fi, ax in roof_pts:
            if ax:
                continue
            d, h, li = signed_nearest(tl, p, 3.0, sign_below=0.25)
            if li in piv:
                piv_min = min(piv_min, d)
            elif d < oth_min:
                oth_min, oth_at = d, p
        pp, po = contacts(t_roof, tl, piv)
        res.append(dict(theta=float(th), pivot=round(piv_min, 4), other=round(oth_min, 4),
                        pivot_overlap=len(pp), other_overlap=len(po),
                        other_at=[round(c, 2) for c in oth_at] if oth_at is not None else None))
    return res


def first_contact(roof, lid, piv, a0, a1, step):
    t_roof = BVHTree.FromBMesh(roof)
    for th in np.arange(a0, a1 + 1e-9, step):
        _, po = contacts(t_roof, lid_tree(lid, rot(th)), piv)
        if po:
            cs = [roof.faces[i].calc_center_median() for i, _ in po]
            return round(float(th), 3), dict(x=[round(min(c.x for c in cs), 2), round(max(c.x for c in cs), 2)],
                                             y=[round(min(c.y for c in cs), 2), round(max(c.y for c in cs), 2)],
                                             z=[round(min(c.z for c in cs), 2), round(max(c.z for c in cs), 2)], n=len(po))
    return None, None


def stop_angle(roof, lid, piv, a0=60, a1=140):
    a, _ = first_contact(roof, lid, piv, a0, a1, 0.5)
    if a is None:
        return None, None
    return first_contact(roof, lid, piv, max(a0, a - 0.5), a, 0.02)


def remove_block(bm):
    """delete the stop blocks (faces inside a block's X span, above the base top, in front of the axis, below Z 63.5)"""
    b = bm.copy()
    b.faces.ensure_lookup_table()
    kill = [f for f in b.faces if any(all(x0 - 0.02 <= v.co.x <= x1 + 0.02 for v in f.verts)
                                      for x0, x1 in (BLOCK_X, (121.6, 129.2)))
            and any(v.co.z > 59.2 + 1e-3 for v in f.verts) and all(v.co.y < 142 and v.co.z < 63.5 for v in f.verts)]
    bmesh.ops.delete(b, geom=kill, context='FACES')
    return b


# ---------------------------------------------------------------- support
def support_columns(bm, cls, top_z=0.2, bot_z=0.2):
    tree = BVHTree.FromBMesh(bm)
    cols = []
    for f in bm.faces:
        if cls.get(f.index) != 'supported':
            continue
        vs = [v.co.copy() for v in f.verts]
        n = max(3, int(f.calc_area() * 20))
        for _ in range(n):
            r1, r2 = random.random(), random.random()
            if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
            p = vs[0] + r1 * (vs[1] - vs[0]) + r2 * (vs[2] - vs[0])
            h = tree.ray_cast(p + Vector((0, 0, -1e-4)), Vector((0, 0, -1)), 100.0)
            if h[0] is None:
                zb, land = BED_Z, 'bed'
            else:
                zb = h[0].z
                ph, rr = polar(h[0])
                if abs(rr - 3.5) < 0.1 and 180 < ph < 360 and any(x0 <= h[0].x <= x1 for x0, x1 in SEATS):
                    land = 'bore_floor'
                elif abs(zb - 59.2) < 0.05:
                    land = 'hinge_base_top'
                else:
                    land = 'model_other'
            ph0, r0 = polar(p)
            inside = r0 < 3.6 and any(x0 <= p.x <= x1 for x0, x1 in SEATS)
            cols.append(dict(x=p.x, y=p.y, z=p.z, zb=zb, h=p.z - zb - top_z - bot_z, land=land,
                             in_channel=inside, phi=ph0, r=r0))
    return cols


def x_escape(tree_full, cols):
    """from support points inside the pivot channel cast +X and -X: distance to first roof surface"""
    out = []
    for c in cols:
        if not c['in_channel']:
            continue
        for zf in (0.25, 0.5, 0.75):
            z = c['zb'] + (c['z'] - c['zb']) * zf
            p = Vector((c['x'], c['y'], z))
            dm = tree_full.ray_cast(p, Vector((-1, 0, 0)), 200.0)
            dp = tree_full.ray_cast(p, Vector((1, 0, 0)), 200.0)
            out.append((c['x'], dm[3] if dm[0] else None, dp[3] if dp[0] else None))
    return out


# ================================================================ main
ONLY_FULL = '--only-full' in sys.argv

if __name__ == '__main__' and not ONLY_FULL:
    roof0 = load_bm(LAB + 'roof_left_hinge_case.stl')
    lid = load_bm(LAB + 'lid_left_hinge_case_closed.stl')
    cls = classify(roof0)
    groups = describe(roof0, cls)
    result = dict(classification=groups,
                  class_area={c: round(sum(roof0.faces[i].calc_area() for i, k in cls.items() if k == c), 2)
                              for c in ('supported', 'droop', 'mild')})
    print('CLASSES', result['class_area'])
    for g in groups:
        print('GROUP', g)

    # support columns on the nominal roof
    cols = support_columns(roof0, cls)
    roof_full = load_bm(LAB + 'roof_full_case.stl')
    t_full = BVHTree.FromBMesh(roof_full)
    esc = x_escape(t_full, cols)
    result['support'] = dict(
        n=len(cols),
        by_land={k: sum(1 for c in cols if c['land'] == k) for k in set(c['land'] for c in cols)},
        in_channel=dict(n=sum(1 for c in cols if c['in_channel']),
                        y=[round(min((c['y'] for c in cols if c['in_channel']), default=0), 2),
                           round(max((c['y'] for c in cols if c['in_channel']), default=0), 2)],
                        top_z=[round(min((c['z'] for c in cols if c['in_channel']), default=0), 2),
                               round(max((c['z'] for c in cols if c['in_channel']), default=0), 2)],
                        base_z=[round(min((c['zb'] for c in cols if c['in_channel']), default=0), 2),
                                round(max((c['zb'] for c in cols if c['in_channel']), default=0), 2)],
                        height=[round(min((c['h'] for c in cols if c['in_channel']), default=0), 2),
                                round(max((c['h'] for c in cols if c['in_channel']), default=0), 2)],
                        land={k: sum(1 for c in cols if c['in_channel'] and c['land'] == k)
                              for k in set(c['land'] for c in cols if c['in_channel'])},
                        floor_phi=[round(min((polar(Vector((0, c['y'], c['zb'])))[0] for c in cols if c['in_channel']), default=0), 1),
                                   round(max((polar(Vector((0, c['y'], c['zb'])))[0] for c in cols if c['in_channel']), default=0), 1)]),
        outside=[dict(y=round(c['y'], 2), z=round(c['z'], 2), zb=round(c['zb'], 2), land=c['land'], phi=round(c['phi'], 1))
                 for c in cols if not c['in_channel']][:400],
        x_escape_min=dict(minus=round(min((e[1] for e in esc if e[1] is not None), default=-1), 2),
                          plus=round(min((e[2] for e in esc if e[2] is not None), default=-1), 2),
                          n=len(esc), none_minus=sum(1 for e in esc if e[1] is None),
                          none_plus=sum(1 for e in esc if e[2] is None)))
    print('SUPPORT', json.dumps({k: v for k, v in result['support'].items() if k != 'outside'}))
    json.dump(cols, open(OUT + '/support_columns.json', 'w'))

    # variants ------------------------------------------------------------
    variants = []
    for exy in (0.0, -0.05, 0.15):
        for sag in (0.0, 0.10, 0.20, 0.30):
            for dr in (0.0, 0.05, 0.10, 0.15):
                if exy != 0.0 and not ((sag, dr) in ((0.0, 0.0), (0.10, 0.05), (0.20, 0.10), (0.30, 0.15))):
                    continue
                variants.append((sag, dr, exy))
    result['variants'] = []
    for sag, dr, exy in variants:
        bm = make_variant(roof0, cls, sag, dr, exy)
        t = BVHTree.FromBMesh(bm)
        st = seated(t)
        th = throat(bm, t)
        bg = bump_gap(t)
        bl = blocking(t)
        v = dict(sag=sag, droop=dr, exy=exy, seated_gap=st['gap'], seated_at_phi=st['at_phi'],
                 ray_gap_min={k: round(min(g for g in rr if g is not None) - R, 4) for k, rr in st['rays'].items()},
                 throat=th, bump_gap=bg, blocking=bl)
        rays = {k: [None if g is None else round(g - R, 4) for g in rr] for k, rr in st['rays'].items()}
        v['ray_gap'] = rays
        result['variants'].append(v)
        print('VAR', sag, dr, exy, 'gap', st['gap'], '@', st['at_phi'], 'throat', th, 'bump', bg, 'block', bl, flush=True)
        if exy == 0.0 and (sag, dr) in ((0.30, 0.15), (0.30, 0.0), (0.20, 0.10)) or (sag, dr, exy) == (0.30, 0.15, 0.15):
            name = f'roof_sag{int(sag*100):02d}_droop{int(dr*100):02d}_xy{int(round(exy*100)):+03d}.stl'
            me = bpy.data.meshes.new(name); bm.to_mesh(me)
            ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
            for o in bpy.context.scene.objects: o.select_set(o == ob)
            bpy.ops.wm.stl_export(filepath=OUT + '/' + name, export_selected_objects=True)
            bpy.data.objects.remove(ob)
        bm.free()

    # full swing for nominal and worst corners ---------------------------
    piv = lid_pivot_faces(lid)
    print('lid pivot faces', len(piv))
    keep_lid = lambda p: p.y > 132 and p.z < 80.5
    keep_roof = lambda p: p.y > 132 and p.z > 59.15
    lid_pts = sample_surface(lid, 6.0, keep_lid)
    result['swing'] = []
    for sag, dr, exy in ((0.0, 0.0, 0.0), (0.10, 0.05, 0.0), (0.20, 0.10, 0.0), (0.30, 0.15, 0.0), (0.30, 0.15, 0.15)):
        bm = make_variant(roof0, cls, sag, dr, exy)
        bm.faces.ensure_lookup_table()
        rpts = sample_surface(bm, 6.0, keep_roof)
        sw = swing(bm, lid, list(range(0, 121, 2)), lid_pts, rpts, piv)
        stp, stp_at = stop_angle(bm, lid, piv)
        nb = remove_block(bm); nb.faces.ensure_lookup_table()
        sec, sec_at = stop_angle(nb, lid, piv, 100, 140)
        early = [r_['theta'] for r_ in sw if r_['other_overlap'] and r_['theta'] < 116]
        rec = dict(sag=sag, droop=dr, exy=exy, stop=stp, stop_at=stp_at, secondary=sec, secondary_at=sec_at,
                   other_contact_before_116=early,
                   pivot_overlap_angles=[r_['theta'] for r_ in sw if r_['pivot_overlap']],
                   pivot_min=min(r_['pivot'] for r_ in sw), pivot_max=max(r_['pivot'] for r_ in sw),
                   other_min_0_118=min(r_['other'] for r_ in sw if r_['theta'] <= 118),
                   other_min_at=min((r_ for r_ in sw if r_['theta'] <= 118), key=lambda r_: r_['other']),
                   curve=sw)
        result['swing'].append(rec)
        print('SWING', sag, dr, exy, 'stop', stp, stp_at, 'secondary', sec, sec_at, 'early', early,
              'pivot clr', rec['pivot_min'], rec['pivot_max'], 'pivot overlaps', len(rec['pivot_overlap_angles']),
              'other_min', rec['other_min_0_118'], rec['other_min_at'], flush=True)
        bm.free(); nb.free()
    json.dump(result, open(OUT + '/results.json', 'w'), indent=1)


def full_parts():
    result = {}
    # full parts: stop and secondary contact (the ~126 deg rear-edge contact is outside the crops) ---
    roofF = load_bm(LAB + 'roof_full_case.stl'); lidF = load_bm(LAB + 'lid_full_case_closed.stl')
    clsF = classify(roofF, region=True)
    pivF = lid_pivot_faces(lidF)
    result['full'] = []
    for sag, dr, exy in ((0.0, 0.0, 0.0), (0.10, 0.05, 0.0), (0.20, 0.10, 0.0), (0.30, 0.15, 0.0), (0.0, 0.15, 0.0),
                         (0.30, 0.15, 0.15), (0.30, 0.15, -0.05)):
        bm = make_variant(roofF, clsF, sag, dr, exy); bm.faces.ensure_lookup_table()
        # the closed lid rests on the roof rim (contact at 0 deg, Z 54.6-56.2), so the scan starts at 20 deg
        stp, stp_at = stop_angle(bm, lidF, pivF, 20, 140)
        nb = remove_block(bm); nb.faces.ensure_lookup_table()
        sec, sec_at = stop_angle(nb, lidF, pivF, 20, 140)
        result['full'].append(dict(sag=sag, droop=dr, exy=exy, stop=stp, stop_at=stp_at, secondary=sec, secondary_at=sec_at))
        print('FULL', sag, dr, exy, 'stop', stp, stp_at, 'secondary', sec, sec_at, flush=True)
        bm.free(); nb.free()
    return result


if __name__ == '__main__':
    full = full_parts()
    json.dump(full, open(OUT + '/results_full.json', 'w'), indent=1)
    print('WROTE', OUT + '/results_full.json')
