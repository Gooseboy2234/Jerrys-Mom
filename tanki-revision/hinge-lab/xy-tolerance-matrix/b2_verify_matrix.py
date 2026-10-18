"""Blender step 2 (headless): independent 3D check of every tolerance corner in matrix.csv.
  blender -b --factory-startup --python b2_verify_matrix.py -- [tag]
For each corner: the tolerance-offset hook profile (profiles.json) is extruded along X over the seat
(30-36.7) as a closed mesh; the lid pivot (diameter change Du + seam blob h at lid-frame angle phi) is
built as a 3D prism and swung 0..120 deg about the real pivot axis with Matrix.Rotation(-theta, 'X').
At each 2-deg step: BVH triangle overlap (binding yes/no) and signed clearance (find_nearest from the
pivot surface vertices; inside = negative, from the face normal). phi is set so the blob passes the
2D worst spot mid-swing. Writes verify{tag}.csv and prints the agreement with the 2D numbers.
"""
import bpy, bmesh, json, csv, math, sys
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TAG = argv[0] if argv and argv[0] != '-' else ''
PART, NPART = (int(argv[1]), int(argv[2])) if len(argv) >= 3 else (0, 1)
AY, AZ = 142.884, 70.0
X0, X1 = 30.0, 36.7           # hook seat
PX0, PX1 = 30.2, 36.5         # pivot length inside the seat
XM = 33.35
profiles = json.load(open(D + f'profiles{TAG}.json'))
piv = json.load(open(D + f'pivot{TAG}.json'))
RB = piv['RB']
rows = list(csv.DictReader(open(D + f'matrix{TAG}.csv')))[PART::NPART]
PIVOT_AXIS = Vector((0, AY, AZ))


def prism(rings, x0, x1):
    """Closed prism from 2D rings (local u, w) -> world (x, AY+u, AZ+w)."""
    bm = bmesh.new()
    for ring in rings:
        if ring[0] == ring[-1]: ring = ring[:-1]
        a = [bm.verts.new((x0, AY + u, AZ + w)) for u, w in ring]
        b = [bm.verts.new((x1, AY + u, AZ + w)) for u, w in ring]
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
        bm.faces.new(a[::-1]); bm.faces.new(b)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    return bm


def pivot_ring(ru, h, phi, n=480):
    """Star-shaped outline of circle ru U blob disc (RB, crest h proud) at angle phi (exact union)."""
    dc = ru + h - RB
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = ru
        if h > 0:
            da = a - math.radians(phi)
            s2 = RB ** 2 - (dc * math.sin(da)) ** 2
            if s2 >= 0 and math.cos(da) > 0:
                r = max(r, dc * math.cos(da) + math.sqrt(s2))
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def inside(tree, v, d=Vector((0.0, 1.0, 0.0))):
    """Ray-parity inside test along +Y in the section plane (robust, unlike the nearest-face normal)."""
    n, o = 0, v.copy()
    for _ in range(64):
        loc, nor, idx, dist = tree.ray_cast(o, d)
        if loc is None: break
        n += 1; o = loc + d * 1e-5
    return n % 2 == 1


def rot_local(pts, theta):
    c, s = math.cos(math.radians(-theta)), math.sin(math.radians(-theta))
    return [(c * u - s * w, s * u + c * w) for u, w in pts]


hook_cache = {}


def hook(key):
    if key not in hook_cache:
        bm = prism(profiles[key], X0, X1)
        hook_cache[key] = (bm, BVHTree.FromBMesh(bm))
    return hook_cache[key]


out = []
worst_diff = 0.0
agree_flag = 0
for r in rows:
    key = f"{r['model']}_{float(r['c']):+.2f}_{float(r['v']):+.2f}"
    bmH, tH = hook(key)
    ru = piv['PIV_R'] + float(r['Du']) / 2
    h = float(r['h'])
    phi = float(r['worst_psi']) + 60.0
    ring0 = pivot_ring(ru, h, phi)
    min_clear, bind_angles = 9.0, []
    for th in range(0, 121, 2):
        ring = rot_local(ring0, th)
        bmP = prism([ring], PX0, PX1)
        tP = BVHTree.FromBMesh(bmP)
        n_ov = len(tP.overlap(tH))
        if n_ov: bind_angles.append(th)
        for u, w in ring:
            v = Vector((XM, AY + u, AZ + w))
            loc, nor, idx, d = tH.find_nearest(v)
            # sign only matters where the meshes actually intersect (BVH overlap); then use ray parity
            sgn = -1.0 if (n_ov and inside(tH, v)) else 1.0
            min_clear = min(min_clear, sgn * d)
        bmP.free()
    c2d = float(r['clear_swing_min'])
    diff = min_clear - c2d
    worst_diff = max(worst_diff, abs(diff))
    flag_ok = (min_clear < 0) == bool(bind_angles)
    agree_flag += flag_ok
    out.append(dict(model=r['model'], c=r['c'], v=r['v'], Du=r['Du'], h=r['h'], phi=round(phi % 360, 1),
                    blender_clear_min=round(min_clear, 4), clear_2d=round(c2d, 4), diff=round(diff, 4),
                    bvh_bind_from=bind_angles[0] if bind_angles else '', bvh_bind_to=bind_angles[-1] if bind_angles else '',
                    bvh_bind_steps=len(bind_angles)))
with open(D + f'verify{TAG}_part{PART}.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
print(f'VERIFY{TAG} part {PART}/{NPART}: {len(out)} corners; max |Blender - 2D| clearance {worst_diff:.4f} mm; '
      f'overlap flag consistent with sign in {agree_flag}/{len(out)}')
print('VERIFY binding corners (BVH overlap during swing):', sum(1 for o in out if o['bvh_bind_steps']))

# EXACT boolean interference volume at the tightest corner, at its worst swing angle
tight = min(out, key=lambda o: o['blender_clear_min'])
r = next(x for x in rows if (x['model'], x['c'], x['v'], x['Du'], x['h']) == (tight['model'], tight['c'], tight['v'], tight['Du'], tight['h']))
key = f"{r['model']}_{float(r['c']):+.2f}_{float(r['v']):+.2f}"
bpy.ops.wm.read_factory_settings(use_empty=True)


def obj_from_bm(bm, name):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob); return ob


hook_ob = obj_from_bm(prism(profiles[key], X0, X1), 'hook')
ring = pivot_ring(piv['PIV_R'] + float(r['Du']) / 2, float(r['h']), float(r['worst_psi']))   # blob AT the worst spot
piv_ob = obj_from_bm(prism([ring], PX0, PX1), 'pivot')
mod = piv_ob.modifiers.new('x', 'BOOLEAN'); mod.operation = 'INTERSECT'; mod.object = hook_ob; mod.solver = 'EXACT'
dg = bpy.context.evaluated_depsgraph_get()
me = piv_ob.evaluated_get(dg).to_mesh()
bm = bmesh.new(); bm.from_mesh(me)
vol = abs(bm.calc_volume()) if len(bm.verts) else 0.0
print(f"EXACT_BOOLEAN tightest corner {tight['model']} c={tight['c']} v={tight['v']} Du={tight['Du']} h={tight['h']}: "
      f"interference volume {vol:.4f} mm3 over the {PX1 - PX0:.1f} mm seat ({vol / (PX1 - PX0):.4f} mm2 section)")
