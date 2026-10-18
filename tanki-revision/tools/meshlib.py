"""Shared helpers for editing the Tanki case STLs with manifold3d (all units mm)."""
import os
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, "..", "original")
OUT = os.path.join(HERE, "..", "revised")


def load(name):
    return trimesh.load(os.path.join(ORIG, name), process=True)


def to_manifold(tm):
    mesh = mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                   tri_verts=np.asarray(tm.faces, dtype=np.uint32))
    m = mf.Manifold(mesh)
    if m.status() != mf.Error.NoError:
        raise RuntimeError(f"not a valid manifold: {m.status()}")
    return m


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def save(m, name):
    tm = to_trimesh(m)
    # Weld float32 round-off, then drop only faces whose corners collapsed together.
    # (Thin-but-valid needle triangles must stay or the surface opens up.)
    tm.merge_vertices(digits_vertex=5)
    f = tm.faces
    tm.update_faces((f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2]))
    tm.remove_unreferenced_vertices()
    parts = tm.split(only_watertight=False)
    if len(parts) > 1:   # zero-volume face pairs left where coplanar faces met
        tm = trimesh.util.concatenate([p for p in parts if abs(p.volume) >= 1e-3])
    tm.export(os.path.join(OUT, name))
    return tm


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def section_xy(tm, z):
    """Even-odd solid region of a horizontal slice, as a shapely geometry."""
    s = tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    region = None
    for loop in s.discrete:
        p = Polygon(loop[:, :2]).buffer(0)
        region = p if region is None else region.symmetric_difference(p)
    return region


def extrude(geom, z0, z1):
    """Extrude a shapely (Multi)Polygon between z0 and z1."""
    polys = getattr(geom, "geoms", [geom])
    contours = []
    for p in polys:
        if p.is_empty:
            continue
        contours.append(np.asarray(p.exterior.coords)[:-1])
        contours += [np.asarray(r.coords)[:-1] for r in p.interiors]
    cs = mf.CrossSection(contours, mf.FillRule.EvenOdd)
    return cs.extrude(z1 - z0).translate([0, 0, z0])


def prism_xy(points, z0, z1):
    """Vertical prism from a 2D polygon (list of xy points)."""
    return extrude(Polygon(points), z0, z1)
