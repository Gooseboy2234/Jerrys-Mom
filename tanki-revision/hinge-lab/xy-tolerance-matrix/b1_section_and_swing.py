"""Blender step 1 (run headless):
  blender -b --factory-startup --python b1_section_and_swing.py
- Sections the roof and lid crops in the case Y-Z plane at the two hook-seat mid planes (bmesh bisect)
  and writes the loops to sections.json (the 2D tolerance work starts from these Blender sections).
- Nominal 3D swing of the real lid crop against the real roof crop (BVH triangle overlap):
  free swing, first contact (stop), and the secondary contact with the stop block removed.
- Growth-aware stop: min surface distance lid<->roof vs angle, so the stop angle for a total
  XY growth g (roof surface + lid surface) is where that distance = g (exact for offset surfaces).
"""
import bpy, bmesh, json, math, sys
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

H = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/'
OUT = H + 'xy-tolerance-matrix/'
AY, AZ = 142.884, 70.0
PIV = Vector((0, AY, AZ))


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=H + name)
    return (set(bpy.data.objects) - before).pop()


def section_loops(obj, x):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    # chain edges into loops
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen, loops = set(), []
    for v0 in adj:
        if v0 in seen: continue
        loop, prev, cur = [v0], None, v0
        seen.add(v0)
        while True:
            nxt = [n for n in adj[cur] if n is not prev and n not in seen]
            if not nxt: break
            prev, cur = cur, nxt[0]; seen.add(cur); loop.append(cur)
        loops.append([(v.co.y, v.co.z) for v in loop])
    bm.free()
    return loops


def bm_world(obj, mat=None, subdiv=0):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    if subdiv:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    if mat is not None:
        bm.transform(mat)
    return bm


def drop_pivots(bm):
    # remove the pivot cylinders (all verts within r 3.3 of the axis) so the distance check
    # sees the stop/secondary surfaces, not the 0.3 pivot-bore running clearance
    kill = [f for f in bm.faces if all((v.co.y - AY) ** 2 + (v.co.z - AZ) ** 2 < 3.3 ** 2 for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    return bm


def lid_mat(deg):
    return Matrix.Translation(PIV) @ Matrix.Rotation(math.radians(-deg), 4, 'X') @ Matrix.Translation(-PIV)


def overlap(bm_a, tree_b):
    return len(BVHTree.FromBMesh(bm_a).overlap(tree_b))


def radial_only(bm):
    # keep faces whose normal lies in the Y-Z plane (|nx| < 0.3): the X-facing faces belong to
    # the 0.3 axial gaps (seat ends vs lid knuckles), which are not this XY test's surfaces
    bm.normal_update()
    kill = [f for f in bm.faces if abs(f.normal.x) >= 0.3]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    return bm


def min_dist(bm_a, tree_a, bm_b, tree_b):
    d = 1e9
    # only gaps that open in the Y-Z plane count (an X-dominant gap is an axial gap, not XY)
    for va, tb in ((bm_a.verts, tree_b), (bm_b.verts, tree_a)):
        for v in va:
            r = tb.find_nearest(v.co)
            if r[0] is not None and abs(r[0].x - v.co.x) <= 0.5 * r[3] + 1e-6:
                d = min(d, r[3])
    return d


bpy.ops.wm.read_factory_settings(use_empty=True)
roof = load('roof_left_hinge_case.stl')
lid = load('lid_left_hinge_case_closed.stl')
out = {'roof': {}, 'lid': {}}
for x in (33.35, 50.65):
    out['roof'][str(x)] = section_loops(roof, x)
    out['lid'][str(x)] = section_loops(lid, x)
json.dump(out, open(OUT + 'sections.json', 'w'))
print('SECTIONS', {k: {x: [len(l) for l in v[x]] for x in v} for k, v in out.items()})

# ---- nominal swing, BVH triangle overlap
roof_bm = bm_world(roof); roof_tree = BVHTree.FromBMesh(roof_bm)
first = None
for a10 in range(0, 1301, 5):          # 0..130 deg in 0.5 deg steps
    a = a10 / 10
    bmL = bm_world(lid, lid_mat(a))
    n = overlap(bmL, roof_tree); bmL.free()
    if n and first is None:
        first = a; break
print(f'NOMINAL_SWING free to {first - 0.5:.1f} deg, first contact at {first:.1f} deg')

# where is that contact? (X range of intersecting roof triangles)
bmL = bm_world(lid, lid_mat(first)); pairs = BVHTree.FromBMesh(bmL).overlap(roof_tree)
roof_bm.faces.ensure_lookup_table()
xs = [v.co.x for _, j in pairs for v in roof_bm.faces[j].verts]
print(f'  contact roof X {min(xs):.2f}-{max(xs):.2f} (stop block is X 38.2-45.8)')

# secondary contact: roof with the stop block region removed
bm2 = bm_world(roof)
kill = [f for f in bm2.faces if all(37.9 < v.co.x < 46.1 for v in f.verts) and
        all(53.8 + 5.1 < v.co.z < 53.8 + 9.4 for v in f.verts) and all(v.co.y < 141.6 for v in f.verts)]
bmesh.ops.delete(bm2, geom=kill, context='FACES')
tree2 = BVHTree.FromBMesh(bm2)
sec = None
for a10 in range(1150, 1401, 5):
    a = a10 / 10
    bmL = bm_world(lid, lid_mat(a)); n = overlap(bmL, tree2); bmL.free()
    if n: sec = a; break
bmL = bm_world(lid, lid_mat(sec)); pairs = BVHTree.FromBMesh(bmL).overlap(tree2)
bm2.faces.ensure_lookup_table()
pts = np.array([tuple(v.co) for _, j in pairs for v in bm2.faces[j].verts])
print(f'SECONDARY (no stop block) first contact at {sec} deg; roof contact bbox X {pts[:,0].min():.1f}-{pts[:,0].max():.1f} '
      f'Y {pts[:,1].min():.1f}-{pts[:,1].max():.1f} Z {pts[:,2].min():.1f}-{pts[:,2].max():.1f}')

# ---- growth-aware stop: distance vs angle near the stop, densified meshes
roofD = bm_world(roof, subdiv=2); roofD_tree = BVHTree.FromBMesh(roofD)
roof2D = bm_world(roof, subdiv=2)
kill = [f for f in roof2D.faces if all(37.9 < v.co.x < 46.1 for v in f.verts) and
        all(53.8 + 5.1 < v.co.z < 53.8 + 9.4 for v in f.verts) and all(v.co.y < 141.6 for v in f.verts)]
bmesh.ops.delete(roof2D, geom=kill, context='FACES'); roof2D_tree = BVHTree.FromBMesh(roof2D)
roofR = radial_only(bm_world(roof, subdiv=2)); roofR_tree = BVHTree.FromBMesh(roofR)
roof2R = radial_only(bm_world(roof, subdiv=2))
kill = [f for f in roof2R.faces if all(37.9 < v.co.x < 46.1 for v in f.verts) and
        all(53.8 + 5.1 < v.co.z < 53.8 + 9.4 for v in f.verts) and all(v.co.y < 141.6 for v in f.verts)]
bmesh.ops.delete(roof2R, geom=kill, context='FACES'); roof2R_tree = BVHTree.FromBMesh(roof2R)
rows = []
for a in np.arange(110.0, 137.01, 0.25):
    bmL = drop_pivots(bm_world(lid, lid_mat(a), subdiv=2)); tL = BVHTree.FromBMesh(bmL)
    bmLr = radial_only(bm_world(lid, lid_mat(a), subdiv=2)); drop_pivots(bmLr); tLr = BVHTree.FromBMesh(bmLr)
    d_stop = 0.0 if len(tL.overlap(roofD_tree)) else min_dist(bmLr, tLr, roofR, roofR_tree)
    d_sec = 0.0 if len(tL.overlap(roof2D_tree)) else min_dist(bmLr, tLr, roof2R, roof2R_tree)
    rows.append((float(a), d_stop, d_sec)); bmL.free()
json.dump(rows, open(OUT + 'stop_distance.json', 'w'))


def angle_at(col, g):
    for a, *d in rows:
        if d[col] <= g + 1e-9: return a
    return None


for g in (0.0, 0.10, 0.15, 0.20, 0.25, 0.30):
    s, s2 = angle_at(0, g), angle_at(1, g)
    print(f'STOP total growth {g:+.2f}: stop at {s} deg, secondary contact at {s2} deg')
