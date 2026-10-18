"""Prepare EXACT-Boolean test cases: the hook section clipped to a 1.2 mm disc around the 2D contact
(keeps Blender's EXACT solver away from the long near-coincident bore/pivot surfaces) + the pivot ring.
Writes exact_cases.json with the 2D overlap area for each case."""
import importlib.util, sys, json, math
import numpy as np
from shapely.geometry import Polygon, Point
sys.argv = sys.argv[:1]
D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
spec = importlib.util.spec_from_file_location('m', D + 'xy_matrix_2d.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def ring(ru, h, phi, n=480):
    dc = ru + h - m.RB; pts = []
    for k in range(n):
        a = 2 * math.pi * k / n; r = ru
        if h > 0:
            da = a - math.radians(phi); s2 = m.RB ** 2 - (dc * math.sin(da)) ** 2
            if s2 >= 0 and math.cos(da) > 0: r = max(r, dc * math.cos(da) + math.sqrt(s2))
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


cases = []
for mdl, c, v, Du, h, psi in [('I', .15, .15, .2, .2, 231), ('I', .15, -.05, 0, .2, 274), ('I', 0, .15, 0, .2, 227),
                              ('P', .15, .15, .2, .2, 37), ('P', 0, 0, 0, .2, 37)]:
    M = m.model_I(c, v) if mdl == 'I' else m.model_P(c)
    P = Polygon(ring(m.PIV_R + Du / 2, h, psi))
    ov = M.intersection(P)
    ctr = ov.centroid if not ov.is_empty else Point(m.pol(3.4, psi))
    clip = M.intersection(ctr.buffer(1.2, quad_segs=32))
    geoms = [g for g in getattr(clip, 'geoms', [clip]) if g.area > 1e-6]
    cases.append(dict(name=f'{mdl} c={c} v={v} Du={Du} h={h} psi={psi}', hook=[list(map(list, g.exterior.coords)) for g in geoms],
                      pivot=ring(m.PIV_R + Du / 2, h, psi), area2d=ov.area))
json.dump(cases, open(D + 'exact_cases.json', 'w'))
for cs in cases: print(cs['name'], 'overlap area 2D %.5f' % cs['area2d'])
