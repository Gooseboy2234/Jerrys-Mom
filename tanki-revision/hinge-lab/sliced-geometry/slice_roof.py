"""Blender 4.2 headless: slice the roof hook region the way the slicer does.
Print frame: Z_print = Z_case - 53.8. Layer k spans [0.2k, 0.2k+0.2]; its section is taken at
mid-layer and extruded over the layer. Output:
  sliced_roof_case.stl   (the layer-stepped roof, back in the CASE frame)
  layers.json            (per-layer section loops in print XY, for 2-D tolerance offsets)
usage: blender -b --factory-startup --python slice_roof.py -- <in.stl> <outdir> [layer_h]
"""
import bpy, bmesh, sys, json, os
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
LH = float(argv[2]) if len(argv) > 2 else 0.20
PHASE = float(argv[3]) if len(argv) > 3 else 0.0   # shift of the layer grid (sensitivity only)
EPS = 1e-4   # nudge the cut plane off exact vertex heights (like a slicer's float rounding)
ZOFF = 53.8
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=SRC)
src = bpy.context.scene.objects[0]
me = src.data
zmax = max(v.co.z for v in me.vertices) - ZOFF
out_bm = bmesh.new()
layers = []
k = 0
while True:
    z0 = max(0.0, PHASE + LH * (k - 1) if PHASE > 0 else LH * k)
    z1 = PHASE + LH * k if PHASE > 0 else LH * (k + 1)
    zm = (z0 + z1) / 2
    k += 1
    if zm >= zmax:
        break
    bm = bmesh.new(); bm.from_mesh(me)
    for v in bm.verts: v.co.z -= ZOFF
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-7, plane_co=(0, 0, zm + EPS), plane_no=(0, 0, 1),
                           clear_inner=True, clear_outer=True)
    # whatever is left is the section (edges at z = zm)
    for f in list(bm.faces):
        bm.faces.remove(f)
    edges = [e for e in bm.edges if abs(e.verts[0].co.z - zm - EPS) < 1e-5 and abs(e.verts[1].co.z - zm - EPS) < 1e-5]
    # chain edges into loops for the json
    loops = []
    used = set()
    for e0 in edges:
        if e0.index in used: continue
        loop = [e0.verts[0]]; cur_v = e0.verts[1]; used.add(e0.index); prev = e0
        while cur_v is not loop[0]:
            loop.append(cur_v)
            nxt = [e for e in cur_v.link_edges if e.index not in used and e in edges]
            if not nxt: break
            prev = nxt[0]; used.add(prev.index); cur_v = prev.other_vert(cur_v)
        loops.append([[round(v.co.x, 6), round(v.co.y, 6)] for v in loop])
    layers.append({'k': k - 1, 'z0': round(z0, 4), 'zm': round(zm, 4), 'z1': round(z1, 4), 'loops': loops, 'open': sum(1 for l in loops if len(l) < 3)})
    bm.free()
    # fill the section (even-odd, holes handled) and extrude it over the layer: a 2-D filled curve
    good = [lp for lp in loops if len(lp) >= 3]
    if good:
        cu = bpy.data.curves.new('C%d' % k, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
        cu.extrude = (z1 - z0) / 2; cu.resolution_u = 1
        for lp in good:
            sp = cu.splines.new('POLY'); sp.points.add(len(lp) - 1)
            for i, (x, y) in enumerate(lp): sp.points[i].co = (x, y, 0, 1)
            sp.use_cyclic_u = True
        ob = bpy.data.objects.new('C%d' % k, cu); bpy.context.scene.collection.objects.link(ob)
        ob.location.z = zm
        dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
        tmp = bpy.data.meshes.new_from_object(ev); tmp.transform(ob.matrix_world)
        out_bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
bmesh.ops.remove_doubles(out_bm, verts=out_bm.verts[:], dist=1e-6)
for v in out_bm.verts: v.co.z += ZOFF
m2 = bpy.data.meshes.new('sliced'); out_bm.to_mesh(m2); out_bm.free()
ob = bpy.data.objects.new('sliced', m2); bpy.context.scene.collection.objects.link(ob)
for o in bpy.context.scene.objects: o.select_set(o is ob)
bpy.context.view_layer.objects.active = ob
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.stl_export(filepath=os.path.join(OUT, 'sliced_roof_case.stl'), export_selected_objects=True)
json.dump({'layer_h': LH, 'zoff': ZOFF, 'layers': layers}, open(os.path.join(OUT, 'layers.json'), 'w'))
print('OPEN_LOOPS', sum(l['open'] for l in layers)); print('SLICED layers', len(layers), 'tris', len(m2.polygons), 'loops total', sum(len(l['loops']) for l in layers))
