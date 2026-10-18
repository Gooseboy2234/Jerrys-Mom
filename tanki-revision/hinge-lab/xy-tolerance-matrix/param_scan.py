"""Scan hinge_hook.py SQUEEZE x CLEAR and report, for the in-spec tolerance box, the worst seated
clearance over the swing (with the seam blob) and the click-squeeze range, in both roof models.
In-spec pivot: Du in [-0.05, 0.20] with Du + h <= 0.20 (blob included in the +0.20 budget).
Stacked (beyond-spec) pivot: Du = +0.20 AND h = +0.20.
    python3 param_scan.py  -> param_scan.csv
"""
import importlib.util, sys, csv, itertools
import numpy as np
import shapely

sys.argv = sys.argv[:1]
D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
spec = importlib.util.spec_from_file_location('m', D + 'xy_matrix_2d.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
S_ORIG = m.S0
DELTAS = [-0.05, 0.0, 0.05, 0.10, 0.15]
PIV = [(Du, h) for Du in (-0.05, 0.0, 0.05, 0.10, 0.15, 0.20) for h in (0.0, 0.1, 0.2) if Du + h <= 0.2001]


def light(M):
    arm, lip = m.gate_pieces(M)
    return arm.distance(lip), M.distance(shapely.geometry.Point(0, 0))


def blob_min(M, ru, h):
    if h <= 0: return M.distance(shapely.geometry.Point(0, 0)) - ru
    qs = shapely.points(np.array([m.pol(ru + h - m.RB, p) for p in range(0, 360)]))
    return min(float((shapely.distance(M, qs) - m.RB).min()), M.distance(shapely.geometry.Point(0, 0)) - ru)


def reset():
    m.S0 = S_ORIG; m.HH.CLEAR = 0.3; m.HH.SQUEEZE = 0.25; m.HH.BUMP_R = 0.6
    m.HH.R_IN = 3.5; m.HH.R_OUT = 6.5


rows = []
for sq, cl in itertools.product([0.25, 0.20, 0.15, 0.125, 0.10, 0.075, 0.05, 0.025, 0.0], [0.30, 0.35, 0.40, 0.45]):
    reset(); m.use_design(cl, sq)
    for mdl in ('I', 'P'):
        clear_in, clear_stack, sq_lo, sq_hi, sq_stack = 9, 9, 9, -9, -9
        for d in DELTAS:
            M = m.model_I(d, d) if mdl == 'I' else m.model_P(d)
            W, _ = light(M)
            for Du, h in PIV + [(0.20, 0.20)]:
                ru = m.PIV_R + Du / 2
                c = blob_min(M, ru, h)
                s0, sb = 2 * ru - W, 2 * ru + h - W
                if (Du, h) == (0.20, 0.20):
                    clear_stack = min(clear_stack, c); sq_stack = max(sq_stack, sb)
                else:
                    clear_in = min(clear_in, c); sq_lo = min(sq_lo, s0); sq_hi = max(sq_hi, sb)
        ok = clear_in >= 0.05 and sq_lo >= 0.10 and sq_hi <= 0.45
        r = dict(SQUEEZE=sq, CLEAR=cl, model=mdl, clear_min_inspec=round(clear_in, 3), squeeze_min=round(sq_lo, 3),
                 squeeze_max_inspec=round(sq_hi, 3), clear_min_stacked=round(clear_stack, 3),
                 squeeze_max_stacked=round(sq_stack, 3), pass_inspec=ok)
        rows.append(r); print(r, flush=True)
with open(D + 'param_scan.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
