"""Blender 4.2 headless: rotate the lid about the pivot axis and find the stop / secondary contacts.

usage: blender -b --factory-startup --python blender_sweep.py -- cases.json results.json

Each case: {name, roof_rest, roof_block|null, lid_body, lid_pivot|null, dir_deg|null, play|null,
            coarse_to (deg, default 100), stop_to (deg, default 140)}
 - roof_block null -> roof faces are classified 'block' if their centroid lies in BLOCK_BOX.
 - the pivot play: the lid is translated by t*u (u = dir_deg in the case Y-Z plane, 0 = +Y rear,
   90 = +Z up) where t = largest free translation of lid_pivot inside roof_rest (found in Blender
   by stepping the pivot mesh along u by 0.0025 mm until its BVH overlaps the roof). 'play' overrides.
 - sweep: 0..coarse_to in 1 deg steps, then 0.25 deg steps to stop_to; first overlapping step for
   'block' and for 'rest' contacts is recorded, then refined by bisection to 0.005 deg.
"""
import bpy, bmesh, sys, json, math, time
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

AY, AZ = 142.884, 70.0
BLOCK_BOXES = [((37.9, 46.1), (132.9, 137.6), (59.15, 63.6)), ((121.3, 129.5), (132.9, 137.6), (59.15, 63.6))]
argv = sys.argv[sys.argv.index('--') + 1:]
CASES, OUT = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
_cache = {}


def load(path):
    """-> (verts np (n,3), polys list, BVHTree in place, face centroids np)"""
    if path in _cache: return _cache[path]
    bpy.ops.wm.stl_import(filepath=path)
    ob = bpy.context.selected_objects[0]
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.transform(ob.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts])
    P = [[v.index for v in f.verts] for f in bm.faces]
    C = np.array([f.calc_center_median()[:] for f in bm.faces])
    tree = BVHTree.FromBMesh(bm)
    bpy.data.objects.remove(ob, do_unlink=True)
    _cache[path] = (V, P, tree, C)
    return _cache[path]


def pose(theta_deg, d=(0.0, 0.0)):
    """case-frame matrix: rotate by -theta about the pivot axis, then translate by d=(dy, dz)."""
    piv = Vector((0, AY, AZ))
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-theta_deg), 4, 'X') @ Matrix.Translation(-piv)
    return Matrix.Translation(Vector((0, d[0], d[1]))) @ R


def tree_at(mesh, M):
    V, P, _, _ = mesh
    A = np.array(M)
    W = V @ A[:3, :3].T + A[:3, 3]
    return BVHTree.FromPolygons(W.tolist(), P, epsilon=0.0)


def in_block(c):
    return any(all(B[i][0] <= c[i] <= B[i][1] for i in range(3)) for B in BLOCK_BOXES)


def contacts(lid, roof_rest, roof_block, theta, d):
    """-> (block_pairs, rest_pairs) overlap lists at this pose.  Pairs are (lid_face, roof_face).
    The roof is moved by the inverse pose into the lid's frame (cheaper: roof meshes are small)."""
    Minv = pose(theta, d).inverted()
    rest = lid[2].overlap(tree_at(roof_rest, Minv))
    if roof_block is not None:
        blk = lid[2].overlap(tree_at(roof_block, Minv))
    else:
        C = roof_rest[3]
        blk = [p for p in rest if in_block(C[p[1]])]
        rest = [p for p in rest if not in_block(C[p[1]])]
    return blk, rest


def play_along(pivot, roof_rest, u, theta=120.0, step=0.01, tmax=1.0, tol=0.0005):
    """Largest free translation of the pivot along u (roof moved into the pivot frame).
    0.01 mm steps until the pivot cuts the seat, then bisection to `tol`."""
    def hit(t):
        return bool(pivot[2].overlap(tree_at(roof_rest, pose(theta, (t * u[0], t * u[1])).inverted())))
    if hit(0.0):
        return 0.0, True
    t = 0.0
    while t < tmax and not hit(t + step):
        t += step
    a, b = t, t + step
    while b - a > tol:
        m = (a + b) / 2
        if hit(m): b = m
        else: a = m
    return a, False


def refine(f, a0, a1, tol=0.005):
    """f(a) True = contact. a0 free, a1 contact."""
    while a1 - a0 > tol:
        m = (a0 + a1) / 2
        if f(m): a1 = m
        else: a0 = m
    return a1


def run(case):
    t_start = time.time()
    rr = load(case['roof_rest'])
    rb = load(case['roof_block']) if case.get('roof_block') else None
    lid = load(case['lid_body'])
    res = {k: v for k, v in case.items()}
    d = (0.0, 0.0)
    if case.get('dir_deg') is not None:
        a = math.radians(case['dir_deg']); u = (math.cos(a), math.sin(a))
        if case.get('play') is not None:
            t, bound = case['play'], False
        else:
            t, bound = play_along(load(case['lid_pivot']), rr, u)
            if case.get('seam'):          # one-sided seam blob at the load-side contact point
                res['play_without_seam'] = round(t, 4)
                t = max(t - case['seam'], 0.0)
        d = (t * u[0], t * u[1])
        res.update(play=round(t, 4), pivot_bound_at_rest=bound, disp=[round(d[0], 4), round(d[1], 4)])
    angles = list(np.arange(0.0, case.get('coarse_to', 100.0), case.get('coarse_step', 2.0))) + \
        list(np.arange(case.get('coarse_to', 100.0), case.get('stop_to', 140.0) + 1e-9, 0.25))
    first_blk = first_rest = None
    prev = 0.0
    rest_where = None
    for th in angles:
        blk, rest = contacts(lid, rr, rb, th, d)
        if blk and first_blk is None:
            first_blk = (prev, th)
        if rest and first_rest is None:
            first_rest = (prev, th)
            C = lid[3]
            # where on the lid (closed-frame centroid of the touching lid faces)
            idx = sorted({p[0] for p in rest})
            cc = C[idx]
            rest_where = [round(float(v), 2) for v in list(cc.min(0)) + list(cc.max(0))]
        if first_blk and first_rest: break
        prev = th
    if first_blk:
        res['stop_step'] = round(float(first_blk[1]), 2)
        res['stop_refined'] = round(refine(lambda a: bool(contacts(lid, rr, rb, a, d)[0]), *first_blk), 3)
    else:
        res['stop_step'] = None
    if first_rest:
        res['secondary_step'] = round(float(first_rest[1]), 2)
        res['secondary_refined'] = round(refine(lambda a: bool(contacts(lid, rr, rb, a, d)[1]), *first_rest), 3)
        res['secondary_lid_faces_bbox_closed'] = rest_where
    else:
        res['secondary_step'] = None
    res['secs'] = round(time.time() - t_start, 2)
    return res


cases = json.load(open(CASES))
out = []
for c in cases:
    r = run(c)
    out.append(r)
    print('RESULT', json.dumps(r), flush=True)
json.dump(out, open(OUT, 'w'), indent=1)
