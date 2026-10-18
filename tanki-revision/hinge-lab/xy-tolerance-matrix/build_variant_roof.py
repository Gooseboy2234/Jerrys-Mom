"""Build a roof-crop STL (case frame, X 24-60, same crop as hinge-lab/roof_left_hinge_case.stl) from
tools/hinge_hook.py with changed parameters, WITHOUT writing anything outside this folder.
    python3 build_variant_roof.py CLEAR SQUEEZE EXIT out.stl"""
import sys
clear, squeeze, exit_deg, out = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
sys.argv = sys.argv[:1]
sys.path.insert(0, '/home/user/Jerrys-Mom/tanki-revision/tools')
import numpy as np, trimesh
import hinge_hook as HH
from meshlib import to_trimesh, box
HH.CLEAR, HH.SQUEEZE, HH.EXIT = clear, squeeze, exit_deg
HH.R_IN = HH.PIVOT_R + HH.CLEAR; HH.R_OUT = HH.R_IN + HH.WALL
roof, _ = HH.build()
crop = roof ^ box(24, 60, 126.0, 400, -50, 100)     # case Y >= 124
tm = to_trimesh(crop)
tm.apply_translation([0, -2.0, 53.8])
tm.export(out)
ref = trimesh.load('/home/user/Jerrys-Mom/tanki-revision/hinge-lab/roof_left_hinge_case.stl')
print(f'built CLEAR {clear} SQUEEZE {squeeze} EXIT {exit_deg}: volume {tm.volume:.3f} (given crop {ref.volume:.3f}), '
      f'bounds {np.round(tm.bounds, 2).tolist()} watertight {tm.is_watertight}')
