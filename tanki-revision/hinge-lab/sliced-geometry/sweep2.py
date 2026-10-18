"""Finer sweep around the candidates from sweep.py (sliced, tolerance corners). usage: python3 sweep2.py [outdir]"""
import sys, json
import sweep as S, analyze as A
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
res = {}
P = S.smooth_profile(CLEAR=0.40, SQUEEZE=0.15)
rows = S.corner_summary.__wrapped__(P) if hasattr(S.corner_summary, '__wrapped__') else None
# which corners give the low clicks for CLEAR 0.40 + SQUEEZE 0.15
import itertools
low = []
for (en, e), ar in itertools.product(S.E.items(), (False, True)):
    Pb = S.slice2d(P, e, ar)
    for pn, (rc, rk) in S.PIV.items():
        m = A.metrics(Pb, rc, rk)
        low.append((m['click_squeeze'], en, pn, 'arachne' if ar else 'geom', m['click_dir']))
low.sort(); print('CLEAR0.40/SQ0.15 lowest clicks', low[:5]); res['clear040_sq015_low'] = low[:8]
for clear, sq in [(0.30, 0.125), (0.30, 0.175), (0.30, 0.20), (0.35, 0.10), (0.35, 0.15), (0.35, 0.20), (0.40, 0.20), (0.40, 0.25)]:
    Pc = S.smooth_profile(CLEAR=clear, SQUEEZE=sq)
    r = S.corner_summary(Pc); res[f'CLEAR {clear} SQ {sq}'] = r
    print(f"CLEAR {clear} SQ {sq}: nom {r['nominal_point']} | clr worst {r['clear_worst']:.3f} no-blob {r['clear_worst_no_blob']:.3f} | click {r['click_min']:.3f}({r['click_min_corner']})..{r['click_max']:.3f}({r['click_max_corner']}) in-window {r['frac_click_in_0.10_0.45']:.2f} | blocks>= {r['block_sector_min']:.2f}", flush=True)
json.dump(res, open(f'{OUT}/sweep2.json', 'w'), indent=1)
