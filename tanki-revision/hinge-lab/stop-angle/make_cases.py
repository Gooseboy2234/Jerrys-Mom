"""Write the tolerance-corner case lists for blender_sweep.py (split into N chunks)."""
import json, itertools, sys
M = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/stop-angle/out/mesh/'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
E = [-0.15, -0.05, 0.0, 0.15]          # surface error, roof and lid (task: +/-0.15; brief: -0.05..+0.15)
# pivot: (uniform radius error, one-sided seam blob at the load-side contact).  Brief: dia -0.05..+0.20
# 'including a seam blob of up to +0.2 on one side' -> r -0.025 / 0 / +0.10 uniform, or nominal + 0.2 blob
EP = [(-0.025, 0.0), (0.0, 0.0), (0.10, 0.0), (0.0, 0.2)]
DY = [-0.05, 0.0, 0.05]                # block positional repeatability (case Y)
DIRS = [0.0, -10.6]                    # pivot load direction: impact (pure rear) / static (rear, 10.6 deg down)


def case(er, el, epp, dy, d, top=0, play=None, tag='main'):
    ep, seam = epp
    c = dict(name=f'{tag}_r{er:+.3f}_l{el:+.3f}_p{ep:+.3f}_s{seam:.1f}_dy{dy:+.2f}_top{top:+d}_dir{d:+.1f}',
             tag=tag, e_roof=er, e_lid=el, e_piv=ep, seam=seam, block_dy=dy, top_layers=top,
             roof_rest=f'{M}roof_rest_r{er:+.3f}.stl', roof_block=f'{M}roof_block_r{er:+.3f}_dy{dy:+.2f}_top{top:+d}.stl',
             lid_body=f'{M}lid_body_l{el:+.3f}.stl', lid_pivot=f'{M}lid_pivot_p{ep:+.3f}.stl', dir_deg=d, coarse_to=100.0, stop_to=145.0)
    if play is not None: c['play'] = play
    return c


cases = [case(*k) for k in itertools.product(E, E, EP, DY, DIRS)]
# block top layer +/-1 at the extreme corners
for er, el, ep in [(0.15, 0.15, (0.0, 0.2)), (-0.15, -0.15, (-0.025, 0.0)), (0, 0, (0.0, 0.0))]:
    for top in (-1, 1):
        cases.append(case(er, el, ep, 0.0, 0.0, top, tag='top'))
# pivot load direction scan (envelope over every direction) at nominal and the two extreme corners
for er, el, ep, dy in [(0, 0, (0.0, 0.0), 0), (-0.15, -0.15, (-0.025, 0.0), -0.05), (0.15, 0.15, (0.0, 0.2), 0.05), (-0.05, -0.05, (-0.025, 0.0), -0.05)]:
    for d in range(-180, 180, 15):
        cases.append(case(er, el, ep, dy, float(d), tag='dirscan'))
chunks = [cases[i::N] for i in range(N)]
for i, ch in enumerate(chunks):
    json.dump(ch, open(f'/home/user/Jerrys-Mom/tanki-revision/hinge-lab/stop-angle/out/cases_{i}.json', 'w'), indent=1)
print(len(cases), 'cases in', N, 'chunks')
