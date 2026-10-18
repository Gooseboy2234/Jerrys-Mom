"""Blender 4.2 checks on NOMINAL vs SLICED roof (case frame):
 1. YZ sections at several X (bmesh.bisect_plane) -> sections.json (for the 2-D metrics)
 2. Seated clearance by BVH: nearest roof surface to the pivot axis, and ray-cast radial gap vs angle
 3. Lid swing 0..130 deg about the pivot axis: first BVH contact (the stop) for each roof
usage: blender -b --factory-startup --python blender_checks.py -- <nominal.stl> <sliced.stl> <lid.stl> <out.json>
"""
import bpy, bmesh, sys, json, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index('--') + 1:]
NOM, SLI, LID, OUTJ = a
AY, AZ, R = 142.884, 70.0, 3.2
XS = [30.5, 33.35, 36.4, 47.6, 50.65, 53.6]
SEAT_X = [(30.2, 36.7), (47.3, 53.8)]   # where pivot and seat overlap

def load(p):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=p)
    me = bpy.context.scene.objects[0].data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    return bm

def sections(bm):
    out = {}
    for x in XS:
        b = bm.copy()
        bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], dist=1e-7,
                               plane_co=(x, 0, 0), plane_no=(1, 0, 0), clear_inner=True, clear_outer=True)
        segs = [[[e.verts[0].co.y, e.verts[0].co.z], [e.verts[1].co.y, e.verts[1].co.z]]
                for e in b.edges if abs(e.verts[0].co.x - x) < 1e-5 and abs(e.verts[1].co.x - x) < 1e-5]
        out[str(x)] = segs; b.free()
    return out

def clearance(bm):
    t = BVHTree.FromBMesh(bm)
    best = (1e9, None)
    for x0, x1 in SEAT_X:
        n = int((x1 - x0) / 0.05)
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            hit = t.find_nearest(Vector((x, AY, AZ)))
            if hit[0] is not None and hit[3] < best[0]:
                best = (hit[3], [round(c, 4) for c in hit[0]])
    rays = {}
    for x in (33.35, 50.65):
        g = []
        for k in range(720):
            th = math.radians(k * 0.5)
            d = Vector((0, math.cos(th), math.sin(th)))
            h = t.ray_cast(Vector((x, AY, AZ)), d, 12.0)
            g.append(round(h[3] - R, 4) if h[0] is not None else None)
        rays[str(x)] = g
    p = best[1]
    ang = math.degrees(math.atan2(p[2] - AZ, p[1] - AY)) % 360 if p else None
    return {'min_gap': round(best[0] - R, 4), 'at': p, 'angle': round(ang, 1) if ang is not None else None, 'rays': rays}

def swing(roof_bm, lid_bm):
    t_roof = BVHTree.FromBMesh(roof_bm)
    piv = Vector((0, AY, AZ))
    res = []
    th = 0.0
    while th <= 130.0 + 1e-9:
        M = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-th), 4, 'X') @ Matrix.Translation(-piv)
        b = lid_bm.copy(); b.transform(M)
        n = len(t_roof.overlap(BVHTree.FromBMesh(b))); b.free()
        res.append((round(th, 2), n))
        th += 0.25
    first = next((t for t, n in res if n > 0 and t > 0), None)
    return {'overlap_at_0': res[0][1], 'first_contact_deg': first,
            'contacts_95_130': [(t, n) for t, n in res if t >= 95 and n > 0][:12]}

R_ = {}
lid = load(LID); lid_c = lid.copy()
for name, path in (('nominal', NOM), ('sliced', SLI)):
    bm = load(path)
    R_[name] = {'sections': sections(bm), 'clearance': clearance(bm)}
    R_[name]['swing'] = swing(bm, lid_c)
    c = R_[name]['clearance']; s = R_[name]['swing']
    print('BL', name, 'min seated gap', c['min_gap'], 'at angle', c['angle'], c['at'],
          '| lid overlap@0', s['overlap_at_0'], 'first contact', s['first_contact_deg'], s['contacts_95_130'][:4])
json.dump(R_, open(OUTJ, 'w'))
