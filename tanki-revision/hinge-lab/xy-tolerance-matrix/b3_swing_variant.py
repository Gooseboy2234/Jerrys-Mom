"""Blender step 3 (headless): 3D swing of the real lid crop against a roof crop (the given one or a
rebuilt parameter variant), BVH triangle overlap at 0.25 deg steps.
  blender -b --factory-startup --python b3_swing_variant.py -- roof.stl [roof2.stl ...]
Reports free swing, first-contact angle and where it is (roof X/Y/Z box)."""
import bpy, bmesh, math, sys
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

H = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/'
AY, AZ = 142.884, 70.0
PIV = Vector((0, AY, AZ))
files = sys.argv[sys.argv.index('--') + 1:]


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    return (set(bpy.data.objects) - before).pop()


def bm_of(obj, mat=None):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    if mat is not None: bm.transform(mat)
    return bm


bpy.ops.wm.read_factory_settings(use_empty=True)
lid = load(H + 'lid_left_hinge_case_closed.stl')
for f in files:
    roof = load(f if f.startswith('/') else H + 'xy-tolerance-matrix/' + f)
    rbm = bm_of(roof); rt = BVHTree.FromBMesh(rbm); rbm.faces.ensure_lookup_table()
    first = None
    for k in range(0, 521):
        a = k * 0.25
        M = Matrix.Translation(PIV) @ Matrix.Rotation(math.radians(-a), 4, 'X') @ Matrix.Translation(-PIV)
        lbm = bm_of(lid, M); pairs = BVHTree.FromBMesh(lbm).overlap(rt); lbm.free()
        if pairs:
            first = a
            pts = [rbm.faces[j].verts[i].co for _, j in pairs for i in range(3)]
            lo = [min(p[i] for p in pts) for i in range(3)]; hi = [max(p[i] for p in pts) for i in range(3)]
            break
    print(f'SWING {f}: free 0-{first - 0.25:.2f} deg, first contact {first:.2f} deg at roof X {lo[0]:.1f}-{hi[0]:.1f} '
          f'Y {lo[1]:.1f}-{hi[1]:.1f} Z {lo[2]:.1f}-{hi[2]:.1f}')
    bpy.data.objects.remove(roof)
