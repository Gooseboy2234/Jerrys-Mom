import bpy, bmesh, mathutils
from mathutils.bvhtree import BVHTree
R='/home/user/Jerrys-Mom/tanki-revision/revised/'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=R+'TEST_hinge_hook_roof_coupon_-_print_ONE.stl')
bpy.ops.wm.stl_import(filepath=R+'TEST_hinge_hook_lid_coupon_-_print_ONE.stl')
objs=[o for o in bpy.context.scene.objects]
for o in objs: print('OBJ',o.name,len(o.data.vertices),[round(v,2) for v in o.dimensions])
a,b=objs
mod=a.modifiers.new('b','BOOLEAN'); mod.operation='INTERSECT'; mod.object=b; mod.solver='EXACT'
dg=bpy.context.evaluated_depsgraph_get(); ev=a.evaluated_get(dg); me=ev.to_mesh()
print('BOOLEAN_INTERSECT_VERTS',len(me.vertices))
bm=bmesh.new(); bm.from_mesh(a.data); t1=BVHTree.FromBMesh(bm)
bm2=bmesh.new(); bm2.from_mesh(b.data); t2=BVHTree.FromBMesh(bm2)
print('BVH_OVERLAP_PAIRS',len(t1.overlap(t2)))
