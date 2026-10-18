"""Aggregate the Blender sweep results: stop-angle envelopes, corners, margins; plots."""
import json, glob, itertools
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/stop-angle/out/'
R = []
for f in sorted(glob.glob(D + 'results_[0-9].json')):
    R += json.load(open(f))
print(len(R), 'cases')
S = {}


def env(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return (min(v), max(v)) if v else (None, None)


def pick(rows, key, fn):
    rows = [r for r in rows if r.get(key) is not None]
    return fn(rows, key=lambda r: r[key])


def brief_range(r):
    return r['e_roof'] >= -0.05 and r['e_lid'] >= -0.05


main = [r for r in R if r['tag'] == 'main']
for label, rows in (('task_pm015', main), ('brief_m005_p015', [r for r in main if brief_range(r)])):
    for d in (0.0, -10.6, None):
        rr = [r for r in rows if d is None or r['dir_deg'] == d]
        k = f'{label}_dir{"all" if d is None else d}'
        lo, hi = pick(rr, 'stop_refined', min), pick(rr, 'stop_refined', max)
        S[k] = dict(n=len(rr), stop_step=env(rr, 'stop_step'), stop_refined=env(rr, 'stop_refined'),
                    secondary_refined=env(rr, 'secondary_refined'), play=env(rr, 'play'),
                    min_margin_secondary_minus_stop=round(min(r['secondary_refined'] - r['stop_refined'] for r in rr), 3),
                    any_secondary_before_stop=any(r['secondary_refined'] <= r['stop_refined'] for r in rr),
                    any_bound=sum(1 for r in rr if r.get('pivot_bound_at_rest')),
                    min_corner={kk: lo[kk] for kk in ('e_roof', 'e_lid', 'e_piv', 'seam', 'block_dy', 'dir_deg', 'play', 'stop_step', 'stop_refined', 'secondary_refined')},
                    max_corner={kk: hi[kk] for kk in ('e_roof', 'e_lid', 'e_piv', 'seam', 'block_dy', 'dir_deg', 'play', 'stop_step', 'stop_refined', 'secondary_refined')})
# nominal reference rows
for r in main:
    if r['e_roof'] == 0 and r['e_lid'] == 0 and r['e_piv'] == 0 and r['seam'] == 0 and r['block_dy'] == 0:
        S[f'nominal_sliced_dir{r["dir_deg"]}'] = {k: r[k] for k in ('play', 'stop_step', 'stop_refined', 'secondary_refined')}
# linear sensitivities from the main factorial (least squares)
X, y, y2 = [], [], []
for r in main:
    if r['dir_deg'] != 0.0: continue
    X.append([1, r['e_roof'], r['e_lid'], r['play'], r['block_dy']]); y.append(r['stop_refined']); y2.append(r['secondary_refined'])
X = np.array(X); c, *_ = np.linalg.lstsq(X, np.array(y), rcond=None); c2, *_ = np.linalg.lstsq(X, np.array(y2), rcond=None)
res = np.array(y) - X @ c
S['fit_stop_deg'] = dict(zip(['const', 'per_mm_e_roof', 'per_mm_e_lid', 'per_mm_play', 'per_mm_block_dy'], np.round(c, 3).tolist()))
S['fit_stop_resid_max'] = round(float(abs(res).max()), 3)
S['fit_secondary_deg'] = dict(zip(['const', 'per_mm_e_roof', 'per_mm_e_lid', 'per_mm_play', 'per_mm_block_dy'], np.round(c2, 3).tolist()))
# top-layer variants
S['top_layer_variants'] = [{k: r[k] for k in ('e_roof', 'e_lid', 'e_piv', 'seam', 'top_layers', 'stop_refined', 'secondary_refined')} for r in R if r['tag'] == 'top']
# direction scan
ds = {}
for r in R:
    if r['tag'] != 'dirscan': continue
    key = f"r{r['e_roof']:+.3f}_l{r['e_lid']:+.3f}_p{r['e_piv']:+.3f}_s{r['seam']:.1f}_dy{r['block_dy']:+.2f}"
    ds.setdefault(key, []).append((r['dir_deg'], r['play'], r['stop_refined'], r['secondary_refined']))
S['dirscan'] = {}
for k, v in ds.items():
    v.sort()
    st = [a[2] for a in v]; sec = [a[3] for a in v]
    S['dirscan'][k] = dict(stop_min=min(st), stop_max=max(st), dir_at_max=v[int(np.argmax(st))][0], dir_at_min=v[int(np.argmin(st))][0],
                           secondary_min=min(sec), min_margin=round(min(b - a for a, b in zip(st, sec)), 3), rows=v)
S['min_secondary_all_cases'] = min(r['secondary_refined'] for r in R)
S['any_contact_before_stop_all_cases'] = [r['name'] for r in R if r['secondary_refined'] <= r['stop_refined']]
S['stop_step_hist_task'] = {str(k): sum(1 for r in main if r['stop_step'] == k) for k in sorted({r['stop_step'] for r in main})}
S['n_over_124_task'] = sum(1 for r in main if r['stop_refined'] > 124)
S['n_over_124_brief'] = sum(1 for r in main if brief_range(r) and r['stop_refined'] > 124)
S['n_under_116'] = sum(1 for r in main if r['stop_refined'] < 116)
S['over_124_rows'] = [{k: r[k] for k in ('e_roof', 'e_lid', 'e_piv', 'seam', 'block_dy', 'dir_deg', 'play', 'stop_refined')} for r in main if r['stop_refined'] > 124]
json.dump(S, open(D + 'summary.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in S.items() if k not in ('dirscan', 'over_124_rows')}, indent=1)); print('over124', len(S['over_124_rows']))
for k, v in S['dirscan'].items():
    print('dirscan', k, {kk: vv for kk, vv in v.items() if kk != 'rows'})

# plots
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for d, mk in ((0.0, 'o'), (-10.6, 'x')):
    rr = [r for r in main if r['dir_deg'] == d]
    xx = [r['e_roof'] + r['e_lid'] + r['block_dy'] for r in rr]
    ax[0].scatter(xx, [r['stop_refined'] for r in rr], c=[r['play'] for r in rr], cmap='viridis', marker=mk, s=18, label=f'load dir {d} deg')
ax[0].axhspan(116, 124, color='g', alpha=.08); ax[0].axhline(126, color='r', ls='--', label='brief 126 deg limit')
ax[0].set_xlabel('e_roof + e_lid + block_dy (mm)  [tab/block surfaces grow toward each other]'); ax[0].set_ylabel('stop angle (deg)')
ax[0].legend(fontsize=8); ax[0].grid(alpha=.3); ax[0].set_title('Stop angle, all corners (colour = pivot play, mm)')
for k, v in S['dirscan'].items():
    a = np.array(v['rows'])
    ax[1].plot(a[:, 0], a[:, 2], '-o', ms=3, label=k)
ax[1].axhspan(116, 124, color='g', alpha=.08); ax[1].axhline(126, color='r', ls='--')
ax[1].set_xlabel('pivot displacement direction (deg, 0 = rear, 90 = up)'); ax[1].set_ylabel('stop angle (deg)')
ax[1].legend(fontsize=7); ax[1].grid(alpha=.3); ax[1].set_title('Stop vs direction the pivot is pushed')
plt.tight_layout(); plt.savefig(D + 'stop_angle_corners.png', dpi=90)
