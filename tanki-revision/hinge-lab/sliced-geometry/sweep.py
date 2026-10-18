"""Design-parameter sweep on the SLICED hook (2-D equivalent of slice_roof.py for the prismatic hook seat).
The hook seat is a prism along X, so the slicer's XY section at mid-layer, cut at a seat X, is exactly the
smooth YZ profile cut by the horizontal line z = mid-layer. This script:
  1. rebuilds the smooth profile from tools/hinge_hook.py (any SQUEEZE/CLEAR/BUMP_R/EXIT),
  2. validates profile + 2-D slicing against the Blender results for the current design,
  3. runs the tolerance corners for candidate parameter changes.
usage: python3 sweep.py [outdir]
"""
import sys, json, math, itertools, importlib
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
sys.path.insert(0, '/home/user/Jerrys-Mom/tanki-revision/tools')
_argv = sys.argv; sys.argv = ['hinge_hook']; hh = importlib.import_module('hinge_hook'); sys.argv = _argv
import analyze as A

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'

def smooth_profile(SQUEEZE=0.25, CLEAR=0.3, BUMP_R=0.6, EXIT=165.0, WALL=3.0, SEATED_GAP=0.27):
    hh.SQUEEZE, hh.CLEAR, hh.BUMP_R, hh.EXIT, hh.WALL, hh.SEATED_GAP = SQUEEZE, CLEAR, BUMP_R, EXIT, WALL, SEATED_GAP
    hh.R_IN = hh.PIVOT_R + CLEAR; hh.R_OUT = hh.R_IN + WALL
    parts, _ = hh.hook_profile_parts()
    P = unary_union([Polygon(p).buffer(0) for p in parts]).difference(Polygon(hh.disc((hh.AY, hh.AZ), hh.R_IN, 96)))
    # roof-file frame (Y = case Y + 2, Z = print Z) -> case frame
    from shapely import affinity
    return affinity.translate(P, -2.0, A.ZOFF).intersection(A.WIN)

def slice2d(P, e=0.0, arachne=False, phase=0.0, lh=0.2):
    rects = []
    k0 = int((A.AZ - 10 - A.ZOFF) / lh) - 1
    for k in range(k0, k0 + int(20 / lh) + 3):
        z0 = A.ZOFF + phase + k * lh; z1 = z0 + lh; zm = (z0 + z1) / 2 + 1e-4
        s = P.intersection(LineString([(A.AY - 12, zm), (A.AY + 12, zm)]))
        iv = sorted((min(c[0] for c in g.coords), max(c[0] for c in g.coords))
                    for g in getattr(s, 'geoms', [s]) if not g.is_empty and g.geom_type == 'LineString')
        merged = []                                   # slice_closing_radius 0.049 closes gaps < 0.098
        for a, b in iv:
            if merged and a - merged[-1][1] < 2 * A.CLOSE: merged[-1][1] = max(merged[-1][1], b)
            else: merged.append([a, b])
        for a, b in merged:
            a, b = a - e, b + e
            if b <= a: continue
            if arachne:
                w = b - a
                if w < 0.10: continue
                if w < 0.34: m = (a + b) / 2; a, b = m - 0.17, m + 0.17
            rects.append(box(a, z0, b, z1))
    return unary_union(rects).buffer(1e-6).buffer(-1e-6).intersection(A.WIN)

E = {'xy-0.05': -0.05, 'xy0': 0.0, 'xy+0.15': 0.15}
PIV = {'d-0.05': (3.175, 3.175), 'd0': (3.2, 3.2), 'd+0.20': (3.3, 3.3), 'blob+0.2': (3.4, 3.3)}
SAG = {'sag0': (0, 0), 'nosup.15': (0.15, 0.15), 'sup.10': (0.10, 0.15), 'sup.30': (0.30, 0.15)}

def corner_summary(P_smooth, sags=('sag0',), phase=0.0, sliced=True):
    rows = {}
    for (en, e), sn, arach in itertools.product(E.items(), sags, (False, True) if sliced else (False,)):
        Pb = slice2d(P_smooth, e, arach, phase) if sliced else (P_smooth.buffer(e, join_style=2, mitre_limit=5) if e else P_smooth)
        Pb = A.add_sag(Pb, *SAG[sn])
        for pn, (rc, rk) in PIV.items():
            m = A.metrics(Pb, rc, rk); m.pop('itf'); m.pop('clear_bins')
            rows[f'{en}|{pn}|{sn}|{"arachne" if arach else "geom"}'] = m
    clr = min(r['clear_min'] for r in rows.values())
    clr_noblob = min(r['clear_min'] for k, r in rows.items() if 'blob' not in k)
    clicks = [r['click_squeeze'] for r in rows.values()]
    blocks = min(min(r['min_itf_up_60_120'], r['min_itf_back_330_30'], r['min_itf_down_240_300']) for r in rows.values())
    worst_clr = min(rows, key=lambda k: rows[k]['clear_min'])
    lo = min(rows, key=lambda k: rows[k]['click_squeeze']); hi = max(rows, key=lambda k: rows[k]['click_squeeze'])
    nom = rows['xy0|d0|sag0|geom'] if 'xy0|d0|sag0|geom' in rows else None
    return {'nominal_point': None if nom is None else {k: nom[k] for k in ('clear_min', 'click_squeeze', 'click_dir', 'window_le_0.45')},
            'clear_worst': clr, 'clear_worst_corner': worst_clr, 'clear_worst_no_blob': clr_noblob,
            'click_min': min(clicks), 'click_min_corner': lo, 'click_max': max(clicks), 'click_max_corner': hi,
            'frac_click_in_0.10_0.45': round(float(np.mean([(0.10 <= c <= 0.45) for c in clicks])), 3),
            'block_sector_min': blocks}

if __name__ == '__main__':
    import json
    res = {}
    BL = json.load(open(f'{OUT}/blender_checks.json'))
    LP = A.layer_polys(json.load(open(f'{OUT}/layers.json'))['layers'])
    Ps = smooth_profile()
    Pn = A.poly_from_segments(BL['nominal']['sections']['33.35']).intersection(A.WIN)
    near = Polygon([(A.AY + 7.5 * math.cos(t), A.AZ + 7.5 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 200)])
    v1 = Ps.intersection(near).symmetric_difference(Pn.intersection(near)).area
    val = {}
    for e in (-0.05, 0.0, 0.15):
        for ar in (False, True):
            a = slice2d(Ps, e, ar).intersection(near); b = A.sliced_profile(LP, 33.35, e, ar).intersection(near)
            val[f'e{e}_arachne{ar}'] = round(a.symmetric_difference(b).area, 5)
    res['validation'] = {'smooth_rebuild_vs_blender_section_symdiff_mm2_r<7.5': round(v1, 5), 'slice2d_vs_blender_layers_symdiff_mm2': val}
    print('VALIDATION', res['validation'])
    # layer-phase sensitivity (current design): the grid is fixed by the 0.20 first layer (phase 0), but
    # any design change that moves the bump crest / seat top relative to the grid acts like a phase shift
    ph = {}
    for phase in (0.0, 0.05, 0.10, 0.15):
        m = A.metrics(slice2d(Ps, phase=phase), 3.2, 3.2)
        ph[phase] = {k: m[k] for k in ('clear_min', 'clear_min_angle', 'click_squeeze', 'click_dir', 'window_le_0.45')}
        print('PHASE', phase, ph[phase])
    res['phase'] = ph
    # candidates
    cands = {
        'current (SQ 0.25, CLEAR 0.30)': {},
        'SQUEEZE 0.15': {'SQUEEZE': 0.15},
        'SQUEEZE 0.10': {'SQUEEZE': 0.10},
        'SQUEEZE 0.05': {'SQUEEZE': 0.05},
        'CLEAR 0.40': {'CLEAR': 0.40},
        'CLEAR 0.40 + SQUEEZE 0.10': {'CLEAR': 0.40, 'SQUEEZE': 0.10},
        'CLEAR 0.40 + SQUEEZE 0.05': {'CLEAR': 0.40, 'SQUEEZE': 0.05},
        'CLEAR 0.40 + SQUEEZE 0.15': {'CLEAR': 0.40, 'SQUEEZE': 0.15},
    }
    res['candidates'] = {}
    for name, kw in cands.items():
        P = smooth_profile(**kw)
        r = {'sliced_no_sag': corner_summary(P), 'sliced_nosupport_droop0.15': corner_summary(P, ('nosup.15',)),
             'smooth_no_sag': corner_summary(P, sliced=False)}
        res['candidates'][name] = r
        for k, v in r.items():
            print(f"{name:<30s} {k:<28s} nom {v['nominal_point']} | clr worst {v['clear_worst']:.3f} ({v['clear_worst_corner']}) no-blob {v['clear_worst_no_blob']:.3f}"
                  f" | click {v['click_min']:.3f}..{v['click_max']:.3f} in-window {v['frac_click_in_0.10_0.45']:.2f} | blocks>= {v['block_sector_min']:.2f}")
    json.dump(res, open(f'{OUT}/sweep.json', 'w'), indent=1)
