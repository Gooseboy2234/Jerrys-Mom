"""Search hinge_hook.py EXIT x SQUEEZE (x CLEAR) for a throat that survives the PRINT model (layer-stepped,
Y-only XY error) over the in-spec tolerance box AND a +-0.03 mm layer-phase margin (slicer sampling /
Z-offset slop). Worst case over: delta in {-0.05..0.15}, Du in [-0.05, 0.20] with Du + h <= 0.20, phase
in {0, +0.03, -0.03}.   python3 robust_scan.py [CLEAR ...] -> robust_scan.csv
"""
import importlib.util, sys, csv, itertools
import numpy as np
import shapely
from shapely.geometry import Point

clears = [float(a) for a in sys.argv[1:]] or [0.45]
sys.argv = sys.argv[:1]
D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
spec = importlib.util.spec_from_file_location('m', D + 'xy_matrix_2d.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
S_ORIG = m.S0
DELTAS = [-0.05, 0.0, 0.05, 0.10, 0.15]
PHASES = [0.0, 0.03, 0.17]
PIV = [(Du, h) for Du in (-0.05, 0.0, 0.05, 0.10, 0.15, 0.20) for h in (0.0, 0.1, 0.2) if Du + h <= 0.2001]


def reset():
    m.S0 = S_ORIG; m.HH.CLEAR = 0.3; m.HH.SQUEEZE = 0.25; m.HH.BUMP_R = 0.6; m.HH.EXIT = 165.0
    m.HH.R_IN = 3.5; m.HH.R_OUT = 6.5


def blob_min(M, ru, h):
    base = M.distance(Point(0, 0)) - ru
    if h <= 0: return base
    qs = shapely.points(np.array([m.pol(ru + h - m.RB, p) for p in range(0, 360, 2)]))
    return min(float((shapely.distance(M, qs) - m.RB).min()), base)


rows = []
for cl, ex, sq in itertools.product(clears, np.arange(158, 172.01, 1.0), np.arange(0.10, 0.301, 0.025)):
    reset(); m.use_design(cl, round(sq, 3), None, float(ex))
    res = {}
    for ph in PHASES:
        lo, hi, clr, lo_nom = 9, -9, 9, None
        for d in DELTAS:
            M = m.model_P(d, phase=ph)
            arm, lip = m.gate_pieces(M)
            W = arm.distance(lip)
            for Du, h in PIV:
                ru = m.PIV_R + Du / 2
                lo = min(lo, 2 * ru - W); hi = max(hi, 2 * ru + h - W)
                clr = min(clr, blob_min(M, ru, h))
            if d == 0.0: lo_nom = 2 * m.PIV_R - W
        res[ph] = (lo, hi, clr, lo_nom)
    lo = min(r[0] for r in res.values()); hi = max(r[1] for r in res.values()); clr = min(r[2] for r in res.values())
    r = dict(CLEAR=cl, EXIT=ex, SQUEEZE=round(sq, 3), sq_nominal_phase0=round(res[0.0][3], 3),
             sq_lo_phase0=round(res[0.0][0], 3), sq_hi_phase0=round(res[0.0][1], 3),
             sq_lo_all=round(lo, 3), sq_hi_all=round(hi, 3), clear_min=round(clr, 3),
             pass_phase0=res[0.0][0] >= 0.10 and res[0.0][1] <= 0.45 and res[0.0][2] >= 0.05,
             pass_with_phase_margin=lo >= 0.10 and hi <= 0.45 and clr >= 0.05)
    rows.append(r); print(r, flush=True)
with open(D + 'robust_scan.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
