"""Blender step 4: EXACT-solver Boolean INTERSECT volume of pivot(with blob) vs hook at chosen corners,
cross-checked against the 2D overlap area x seat length.
  python3 exact_cases.py && blender -b --factory-startup --python b4_exact_boolean.py"""
import bpy, bmesh, json, math, sys
D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
AY, AZ = 142.884, 70.0
X0, X1, PX0, PX1 = 30.0, 36.7, 30.2, 36.5
RB = 0.3


def prism(rings, x0, x1):
    """Closed prism from 2D rings (local u, w) -> world (x, AY+u, AZ+w)."""
    bm = bmesh.new()
    for ring in rings:
        if ring[0] == ring[-1]: ring = ring[:-1]
        clean = [ring[0]]
        for q in ring[1:]:                      # drop near-duplicate points (degenerate faces upset EXACT)
            if math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) > 2e-4: clean.append(q)
        if math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) <= 2e-4: clean.pop()
        ring = clean
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


cases = json.load(open(D + 'exact_cases.json'))
for cs in cases:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def ob(bm, name):
        me = bpy.data.meshes.new(name); bm.to_mesh(me); o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o); return o
    hk = ob(prism(cs['hook'], X0, X1), 'hook')
    pv = ob(prism([cs['pivot']], PX0, PX1), 'pivot')
    md = pv.modifiers.new('x', 'BOOLEAN'); md.operation = 'INTERSECT'; md.object = hk; md.solver = 'EXACT'
    me = pv.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    bm = bmesh.new(); bm.from_mesh(me)
    vol = abs(bm.calc_volume()) if len(bm.verts) else 0.0
    print(f"EXACT {cs['name']}: Blender intersect volume {vol:.4f} mm3 = {vol / (PX1 - PX0):.5f} mm2 x {PX1 - PX0:.1f} mm; "
          f"2D overlap {cs['area2d']:.5f} mm2")
