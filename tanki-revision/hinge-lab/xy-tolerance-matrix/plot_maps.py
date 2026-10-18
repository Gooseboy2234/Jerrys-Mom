"""Safe-region maps from matrix*.csv -> map_<tag>.png. Each cell = one tolerance corner, coloured by its
worst verdict (status colours, always with a text label), text = click squeeze range / min swing clearance."""
import csv, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch

D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
STATUS = {'JAM': ('#d03b3b', 'JAM'), 'BIND': ('#ec835a', 'BIND'), 'HARD_CLICK': ('#fab219', 'HARD'),
          'NO_CLICK': ('#fab219', 'NOCLK'), 'FALLS_OUT': ('#d03b3b', 'FALLS'), 'OK': ('#0ca30c', 'OK')}
ORDER = ['JAM', 'FALLS_OUT', 'BIND', 'HARD_CLICK', 'NO_CLICK', 'OK']
DU = ['-0.05', '0.0', '0.05', '0.1', '0.15', '0.2']


def worst(verdict):
    fl = verdict.split('+')
    for k in ORDER:
        if k in fl: return k
    return 'OK'


def panel(ax, rows, ylabels, title):
    for i, r_row in enumerate(rows):
        for j, r in enumerate(r_row):
            w = worst(r['verdict'])
            col, lab = STATUS[w]
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=col, edgecolor='white', linewidth=2))
            txt = f"{lab}{' R' if 'RATTLE' in r['verdict'] else ''}\nsq {float(r['sq_noblob']):.2f}-{float(r['sq_blob']):.2f}\ncl {float(r['clear_swing_min']):+.2f}"
            ax.text(j + 0.5, i + 0.5, txt, ha='center', va='center', fontsize=6.2, color='#1a1a19')
            if r['in_spec'] == 'False':
                ax.add_patch(Rectangle((j + 0.04, i + 0.04), 0.92, 0.92, fill=False, edgecolor='#1a1a19', linewidth=0.8, linestyle=':'))
    ax.set_xlim(0, len(DU)); ax.set_ylim(len(rows), 0)
    ax.set_xticks([j + 0.5 for j in range(len(DU))]); ax.set_xticklabels([f'{float(d):+.2f}' for d in DU], fontsize=8)
    ax.set_yticks([i + 0.5 for i in range(len(rows))]); ax.set_yticklabels(ylabels, fontsize=7.5)
    ax.set_xlabel('lid pivot diameter change Du (mm)', fontsize=8.5)
    ax.set_title(title, fontsize=9.5, loc='left')
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)


def make(tag, label):
    R = list(csv.DictReader(open(D + f'matrix{tag}.csv')))
    get = lambda mdl, c, v, du, h: next(r for r in R if r['model'] == mdl and float(r['c']) == c and float(r['v']) == v
                                       and float(r['Du']) == float(du) and float(r['h']) == h)
    CV = [(c, v) for c in (-0.05, 0, 0.05, 0.10, 0.15) for v in (-0.05, 0, 0.05, 0.10, 0.15)]
    fig = plt.figure(figsize=(17, 15), facecolor='white')
    gs = fig.add_gridspec(2, 3, height_ratios=[25, 5], hspace=0.18, wspace=0.28)
    for k, h in enumerate((0.0, 0.1, 0.2)):
        ax = fig.add_subplot(gs[0, k])
        panel(ax, [[get('I', c, v, du, h) for du in DU] for c, v in CV], [f'c {c:+.2f} / v {v:+.2f}' for c, v in CV],
              f'Isotropic model (literal brief), seam blob h = {h:.1f}')
        if k == 0: ax.set_ylabel('roof hook: concave shrink c / convex grow v (mm)', fontsize=8.5)
        ax2 = fig.add_subplot(gs[1, k])
        panel(ax2, [[get('P', d, d, du, h) for du in DU] for d in (-0.05, 0, 0.05, 0.10, 0.15)],
              [f'delta {d:+.2f}' for d in (-0.05, 0, 0.05, 0.10, 0.15)], f'Print model (0.2 layers, Y-only XY error), h = {h:.1f}')
        if k == 0: ax2.set_ylabel('roof XY error', fontsize=8.5)
    fig.suptitle(f'XY tolerance matrix - {label}.  sq = click squeeze (no blob - blob across throat), cl = min seated clearance over 0-120 deg (worst seam angle).'
                 '\nPass: cl >= 0.05, 0.10 <= sq <= 0.45.  R = radial play > 0.35 (rattle note).  Dotted outline = pivot beyond spec (Du + h > 0.20).',
                 fontsize=10.5, x=0.01, ha='left')
    fig.legend(handles=[Patch(color=STATUS[k][0], label=f'{STATUS[k][1]}') for k in ('OK', 'HARD_CLICK', 'BIND', 'JAM')],
               loc='upper right', ncol=4, fontsize=9, frameon=False)
    fig.savefig(D + f'map{tag or "_current"}.png', dpi=110, bbox_inches='tight')


make('', 'CURRENT design (CLEAR 0.30, SQUEEZE 0.25, EXIT 165)')
make('_propA', 'PROPOSAL A (CLEAR 0.45, SQUEEZE 0.20, EXIT 177)')
make('_propB', 'PROPOSAL B (CLEAR 0.45 only; SQUEEZE 0.25, EXIT 165)')
print('ok')
