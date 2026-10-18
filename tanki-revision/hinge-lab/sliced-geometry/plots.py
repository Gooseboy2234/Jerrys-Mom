"""Figures: smooth vs sliced profile (with Ø6.4 pivot), radial clearance vs angle, lift-out interference vs direction."""
import json, math, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import analyze as A
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
C1, C2, INK, MUTED = '#2a78d6', '#eb6834', '#2b2b29', '#8a897f'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False})
BL = json.load(open(f'{OUT}/blender_checks.json'))
LP = A.layer_polys(json.load(open(f'{OUT}/layers.json'))['layers'])
Pn = A.poly_from_segments(BL['nominal']['sections']['33.35']).intersection(A.WIN)
Ps = A.sliced_profile(LP, 33.35)
M = json.load(open(f'{OUT}/metrics.json'))
mn, ms = M['nominal_x33.35'], M['sliced_x33.35']

fig, ax = plt.subplots(1, 2, figsize=(12, 6))
for a, lim in ((ax[0], (A.AY - 8, A.AY + 8, A.AZ - 8, A.AZ + 8)), (ax[1], (A.AY - 4, A.AY + 0.5, A.AZ - 4, A.AZ + 4.5))):
    for g in getattr(Ps, 'geoms', [Ps]):
        x, y = g.exterior.xy; a.fill(x, y, color=C2, alpha=0.25, lw=0); a.plot(x, y, color=C2, lw=1, label='sliced 0.20 mm layers')
    for g in getattr(Pn, 'geoms', [Pn]):
        x, y = g.exterior.xy; a.plot(x, y, color=C1, lw=1.5, label='nominal (smooth STL)')
    t = np.linspace(0, 2 * np.pi, 300)
    a.plot(A.AY + 3.2 * np.cos(t), A.AZ + 3.2 * np.sin(t), color=INK, lw=1, ls='--', label='pivot Ø6.4')
    for zb in np.arange(53.8 + 0.2 * int((lim[2] - 53.8) / 0.2), lim[3], 0.2):
        a.axhline(zb, color=MUTED, lw=0.2, alpha=0.4)
    a.set_xlim(lim[0], lim[1]); a.set_ylim(lim[2], lim[3]); a.set_aspect('equal')
    a.set_xlabel('case Y (mm)'); a.set_ylabel('case Z (mm)')
h, l = ax[0].get_legend_handles_labels(); d = dict(zip(l, h)); ax[0].legend(d.values(), d.keys(), loc='lower left', frameon=False)
ax[0].set_title('Roof hook, YZ section at X 33.35 (seat 1)', loc='left', color=INK)
ax[1].set_title('Throat close-up: arm tip (top) and bump crest (bottom)', loc='left', color=INK)
plt.tight_layout(); plt.savefig(f'{OUT}/profile_nominal_vs_sliced.png', dpi=130)

fig, ax = plt.subplots(2, 1, figsize=(10, 7))
ang = np.arange(360)
cn = np.array([np.nan if v is None else v for v in mn['clear_bins']]); cs = np.array([np.nan if v is None else v for v in ms['clear_bins']])
ax[0].plot(ang, cn, color=C1, lw=2, label='nominal'); ax[0].plot(ang, cs, color=C2, lw=2, label='sliced')
ax[0].axhline(0.05, color=MUTED, lw=1, ls=':'); ax[0].text(2, 0.06, 'pass floor 0.05', color=MUTED)
ax[0].set_ylim(0, 0.5); ax[0].set_xlim(0, 360); ax[0].set_ylabel('radial clearance to Ø6.4 pivot (mm)')
ax[0].set_title('Seated clearance by angle (0 = rear, 90 = up, 180 = front; throat ≈ 105–225 deg has no wall)', loc='left', color=INK)
ax[0].legend(frameon=False, loc='upper right')
phi = A.PHIS
ax[1].plot(phi, mn['itf'], color=C1, lw=2, label='nominal'); ax[1].plot(phi, ms['itf'], color=C2, lw=2, label='sliced')
ax[1].axhspan(0.10, 0.45, color=MUTED, alpha=0.15); ax[1].text(5, 0.5, 'click window 0.10–0.45', color=MUTED)
ax[1].set_ylim(0, 2.5); ax[1].set_xlim(0, 360); ax[1].set_xlabel('straight lift-out direction (deg)')
ax[1].set_ylabel('interference to pass (mm, capped 6.4)'); ax[1].legend(frameon=False, loc='upper right')
ax[1].set_title('Lift-out interference vs direction', loc='left', color=INK)
plt.tight_layout(); plt.savefig(f'{OUT}/clearance_and_liftout.png', dpi=130)
print('plots written')
