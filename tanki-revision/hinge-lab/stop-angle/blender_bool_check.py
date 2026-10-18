"""Blender EXACT-boolean cross-check of the nominal (raw STL, no tolerances) contact angles,
and of the nominal seated clearance (pivot translated inside the seat).

usage: blender -b --factory-startup --python blender_bool_check.py -- out.json
"""
import bpy, bmesh, sys, json, math
from mathutils import Matrix, Vector

H = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/'
OUT = sys.argv[sys.argv.index('--') + 1:][0]
AY, AZ = 142.884, 70.0
bpy.ops.wm.read_factory_settings(use_empty=True)


def imp(p):
    bpy.ops.wm.stl_import(filepath=p)
    return bpy.context.selected_objects[0]


roof = imp(H + 'roof_left_hinge_case.stl')
lid = imp(H + 'lid_left_hinge_case_closed.stl')
# block-free roof copy: subtract a box around the stop block
bpy.ops.mesh.primitive_cube_add(size=1)
cut = bpy.context.active_object
cut.scale = (8.2, 4.7, 4.4); cut.location = (37.9 + 4.1, 132.9 + 2.35, 59.15 + 2.2)
roof_nb = roof.copy(); roof_nb.data = roof.data.copy(); bpy.context.collection.objects.link(roof_nb)
m = roof_nb.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cut; m.solver = 'EXACT'
cut.hide_set(True)


def inter_vol(a, target, M):
    a.matrix_world = M
    tmp = target.copy(); tmp.data = target.data.copy(); bpy.context.collection.objects.link(tmp)
    if target.modifiers:
        # bake the target's modifiers first
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
        tmp.modifiers.clear(); tmp.data = me
    mod = tmp.modifiers.new('i', 'BOOLEAN'); mod.operation = 'INTERSECT'; mod.object = a; mod.solver = 'EXACT'
    dg = bpy.context.evaluated_depsgraph_get()
    me = tmp.evaluated_get(dg).to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(tmp.matrix_world)
    v = abs(bm.calc_volume(signed=True)) if bm.faces else 0.0
    bm.free(); tmp.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(tmp, do_unlink=True)
    return v


def pose(th, d=(0, 0)):
    piv = Vector((0, AY, AZ))
    return Matrix.Translation(Vector((0, d[0], d[1]))) @ Matrix.Translation(piv) @ \
        Matrix.Rotation(math.radians(-th), 4, 'X') @ Matrix.Translation(-piv)


res = {'stop_block_volume': {}, 'secondary_no_block_volume': {}}
for th in (119.0, 119.25, 119.5, 119.75, 120.0):
    res['stop_block_volume'][th] = round(inter_vol(lid, roof, pose(th)), 4)
for th in (126.0, 130.0, 135.25, 136.0, 137.0, 137.5, 137.75, 138.0, 139.0):
    res['secondary_no_block_volume'][th] = round(inter_vol(lid, roof_nb, pose(th)), 4)
# seated clearance: translate the closed lid (pivots) rear / up / down / front until the pivots
# start to cut the seats (block-free roof; lid at 0 deg is clear of everything else nearby)
cl = {}
for name, u in (('rear', (1, 0)), ('up', (0, 1)), ('down', (0, -1))):
    lo, hi = 0.0, 0.6
    for _ in range(12):
        mid = (lo + hi) / 2
        if inter_vol(lid, roof_nb, pose(0.0, (mid * u[0], mid * u[1]))) > 1e-5: hi = mid
        else: lo = mid
    cl[name] = round(lo, 4)
res['seated_clearance_raw'] = cl
print('BOOLCHECK', json.dumps(res))
json.dump(res, open(OUT, 'w'), indent=1)
