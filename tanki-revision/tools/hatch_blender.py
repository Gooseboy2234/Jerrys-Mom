"""Blender (headless) script: make the access hatch 10% bigger.

  blender -b --factory-startup --python tools/hatch_blender.py

Writes, into revised/:
  15_Removable_maintenance_hatch_110_-_print_ONE.stl    scaled hatch (same print orientation)
  02_..._hook15_hatch110_-_print_ONE.stl                roof with the matching bigger opening
and prints volume and bounds checks. Geometry numbers live in hatch_params.py.
"""
import os
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/home/user/Jerrys-Mom/tanki-revision/tools"
sys.path.insert(0, HERE)
import hatch_params as P

ORIG = os.path.join(HERE, "..", "original")
OUT = os.path.join(HERE, "..", "revised")
ROOF_IN = "02_R3_top_vents_back_20mm_bevel4_open120_hook15_-_print_ONE.stl"
ROOF_OUT = "02_R3_top_vents_back_20mm_bevel4_open120_hook15_hatch110_-_print_ONE.stl"
HATCH_IN = "15_Removable_maintenance_hatch_-_print_ONE.stl"
HATCH_OUT = "15_Removable_maintenance_hatch_110_-_print_ONE.stl"


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_stl(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    return [o for o in bpy.data.objects if o not in before][0]


def export_stl(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, ascii_format=False, apply_modifiers=False)


def volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    v = bm.calc_volume(signed=True)
    bm.free()
    return v


def bounds(obj):
    c = np.array([v.co[:] for v in obj.data.vertices])
    return c.min(0), c.max(0)


def check(tag, obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad = sum(1 for e in bm.edges if not e.is_manifold)
    print("CHECK", tag, "faces", len(bm.faces), "non-manifold edges", bad)
    bm.free()
    assert bad == 0, tag


def box(name, x, y, z):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(x[1] - x[0], y[1] - y[0], z[1] - z[0]), verts=bm.verts)
    bmesh.ops.translate(bm, vec=((x[0] + x[1]) / 2, (y[0] + y[1]) / 2, (z[0] + z[1]) / 2), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def cylinder(name, c, r, z, segs=96):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=z[1] - z[0])
    bmesh.ops.translate(bm, vec=(c[0], c[1], (z[0] + z[1]) / 2), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def boolean(target, tool, op):
    m = target.modifiers.new("b", "BOOLEAN")
    m.operation = op
    m.object = tool
    m.solver = "EXACT"
    m.use_self = True            # the roof has touching shells (hook posts on the hinge bases); without this the result tears
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


# ---------------------------------------------------------------- hatch
clear()
hatch = import_stl(os.path.join(ORIG, HATCH_IN))
v0 = volume(hatch)
b0 = bounds(hatch)
Bm = P.B()
hatch.data.transform(Matrix(Bm.tolist()))
lo, hi = bounds(hatch)
hatch.data.transform(Matrix.Translation(-lo))       # keep the supplied print orientation, min corner at the origin
hatch.data.update()
check("hatch", hatch)
export_stl(hatch, os.path.join(OUT, HATCH_OUT))
b1 = bounds(hatch)
print("HATCH size before", np.round(b0[1] - b0[0], 3).tolist(), "after", np.round(b1[1] - b1[0], 3).tolist(),
      "volume", round(v0, 1), "->", round(volume(hatch), 1))
np.save(os.path.join(HERE, "hatch_new_min.npy"), lo)      # hatch-frame offset removed above, for the fit check

# ---------------------------------------------------------------- roof
clear()
roof = import_stl(os.path.join(OUT, ROOF_IN))
vr0 = volume(roof)
H, R, N, OH, OR, ON = P.NEW_HOLE, P.NEW_REBATE, P.NEW_NOTCH, P.OLD_HOLE, P.OLD_REBATE, P.OLD_NOTCH

# 1. fill the old opening (hole + rebate + notch) back to plain plate, exactly flush with both faces
pad = 0.01
fill_a = box("fill_a", (OR["x"][0] - pad, OR["x"][1] + pad), (OR["y"][0] - pad, OR["y"][1] + pad), P.PLATE_Z)
fill_n = cylinder("fill_n", ON["c"], ON["r"] + pad, P.PLATE_Z)
boolean(roof, fill_a, "UNION")
boolean(roof, fill_n, "UNION")
vr1 = volume(roof)
check("opening filled", roof)

# 2. cut the new opening: through-hole, rebate on top, finger notch through both
zlo, zhi = P.PLATE_Z[0] - 1.0, P.PLATE_Z[1] + 1.0
boolean(roof, box("hole", H["x"], H["y"], (zlo, OR["z"][0])), "DIFFERENCE")
boolean(roof, box("rebate", R["x"], R["y"], (OR["z"][0], zhi)), "DIFFERENCE")
boolean(roof, cylinder("notch", N["c"], N["r"], (zlo, zhi)), "DIFFERENCE")
vr2 = volume(roof)
check("new opening cut", roof)
export_stl(roof, os.path.join(OUT, ROOF_OUT))
lo, hi = bounds(roof)
print("ROOF bounds", np.round(lo, 2).tolist(), np.round(hi, 2).tolist())
print("ROOF volume original %.1f | opening filled %.1f (+%.1f) | new opening cut %.1f (%.1f)" % (vr0, vr1, vr1 - vr0, vr2, vr2 - vr1))
print("NEW hole", {k: np.round(v, 2).tolist() for k, v in H.items()}, "rebate", {k: np.round(v, 2).tolist() for k, v in R.items()}, "notch", N)
