"""2-D parameter scan for a sag-tolerant hook: rebuild the hook profile with tools/hinge_hook.py's own
profile code (read-only import, nothing is written outside this folder) for different CLEAR / SQUEEZE /
EXIT, apply the support-sag / droop rule of check2d.sag2d, and measure seated gap, click squeeze
(2-D bottleneck), up/back/down blocking.
First row = current parameters; it must reproduce the STL section (gap 0.298, throat 6.109).
usage: python3 fix_scan.py <out_dir>
"""
import sys, json, itertools
import numpy as np
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/support-sag/out'
sys.argv = ['hinge_hook.py']            # hinge_hook reads EXIT from argv at import
sys.path.insert(0, '/home/user/Jerrys-Mom/tanki-revision/tools')
import hinge_hook as hh
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
sys.path.insert(0, '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/support-sag')
from check2d import sag2d, bottleneck, bump_gap, section, hook_only, LAB, AY, AZ, R


def profile(clear=0.3, squeeze=0.25, exit_deg=165.0, wall=3.0, bump_r=0.6):
    hh.CLEAR, hh.SQUEEZE, hh.EXIT, hh.WALL, hh.BUMP_R = clear, squeeze, exit_deg, wall, bump_r
    hh.R_IN = hh.PIVOT_R + clear
    hh.R_OUT = hh.R_IN + wall
    parts, info = hh.hook_profile_parts()
    polys = [Polygon([(y - 2.0, z + 53.8) for y, z in p]).buffer(0) for p in parts]
    base = Polygon([(124, 53.8), (146.88, 53.8), (146.88, 59.2), (124, 59.2)])  # hinge base (section)
    bore = Polygon([(y - 2.0, z + 53.8) for y, z in hh.disc((hh.AY, hh.AZ), hh.R_IN, 96)])
    g = unary_union(polys + [base]).difference(bore)
    return hook_only(g), info


def blocked(poly, deg, r=R, smax=8.0, ds=0.01):
    """straight push from the seated centre: interference = r - min signed distance, capped at 2r"""
    u = np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])
    m = 1e9
    for s in np.arange(0, smax, ds):
        c = Point(AY + s * u[0], AZ + s * u[1])
        d = c.distance(poly.exterior) * (-1 if poly.contains(c) else 1)
        m = min(m, d)
    return round(min(r - m, 2 * r), 3)


def measure(poly, sag, droop, exy=0.0):
    p = sag2d(poly, sag, droop, exy)[0] if (sag or droop or exy) else poly
    w = bottleneck(p)
    return dict(gap=round(Point(AY, AZ).distance(p) - R, 4), throat=round(w, 4), squeeze=round(6.4 - w, 4),
                bump=round(bump_gap(p), 4))


if __name__ == '__main__':
    rows = []
    stl = hook_only(section(LAB + 'roof_left_hinge_case.stl'))
    ref = measure(stl, 0, 0)
    cur, _ = profile()
    chk = measure(cur, 0, 0)
    print('STL section', ref, '| regenerated current params', chk, '| sym diff area', round(cur.symmetric_difference(stl).area, 4))
    cands = [dict(clear=c, squeeze=q, exit_deg=e) for c, q, e in itertools.product(
        (0.30, 0.35, 0.40, 0.45), (0.25, 0.15, 0.10, 0.05, 0.0, -0.05), (165.0,))]
    cands += [dict(clear=0.40, squeeze=0.05, exit_deg=e) for e in (150.0, 135.0)]
    for c in cands:
        poly, info = profile(**c)
        r = dict(c, arm_end=round(info[0], 1))
        for tag, sag, dr, e in (('nom', 0, 0, 0), ('s10', 0.10, 0.05, 0), ('s20', 0.20, 0.10, 0), ('s30', 0.30, 0.15, 0),
                                ('s30xy+15', 0.30, 0.15, 0.15), ('s10xy-05', 0.10, 0.05, -0.05)):
            r[tag] = measure(poly, sag, dr, e)
        p30 = sag2d(poly, 0.10, 0.05)[0]
        r['block_s10'] = {k: blocked(p30, d) for k, d in (('up', 90), ('back', 0), ('down', 270))}
        rows.append(r)
        print(c, 'arm_end', r['arm_end'], {k: (v['gap'], v['squeeze']) for k, v in r.items() if isinstance(v, dict) and 'gap' in v},
              'block', r['block_s10'], flush=True)
    json.dump(dict(stl=ref, regenerated=chk, rows=rows), open(OUT + '/fix_scan.json', 'w'), indent=1)
