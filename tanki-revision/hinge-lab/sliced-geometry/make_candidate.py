"""Write a hook-seat prism (X 30..36.7, case frame) for a candidate CLEAR/SQUEEZE so Blender can slice it.
usage: python3 make_candidate.py CLEAR SQUEEZE out.stl"""
import sys, numpy as np, trimesh
import sweep as S
clear, sq, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
P = S.smooth_profile(CLEAR=clear, SQUEEZE=sq).buffer(0)
P = max(getattr(P, 'geoms', [P]), key=lambda g: g.area)
m = trimesh.creation.extrude_polygon(P, 6.7)            # polygon in (Y,Z), extruded along +third axis
v = m.vertices.copy(); m.vertices = np.c_[v[:, 2] + 30.0, v[:, 0], v[:, 1]]
if m.volume < 0: m.invert()
m.export(out); print('wrote', out, m.is_watertight, m.bounds.round(3).tolist())
