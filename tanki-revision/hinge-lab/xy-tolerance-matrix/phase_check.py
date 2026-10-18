"""Layer-phase robustness of the P (print) model: shift the layer grid by 0..0.2 mm (as if the hook
axis landed at a different height within a layer, or the slicer sampled differently).
    python3 phase_check.py [CLEAR SQUEEZE]"""
import importlib.util, sys
import numpy as np
args = [float(a) for a in sys.argv[1:3]]
sys.argv = sys.argv[:1]
D = '/home/user/Jerrys-Mom/tanki-revision/hinge-lab/xy-tolerance-matrix/'
spec = importlib.util.spec_from_file_location('m', D + 'xy_matrix_2d.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
if args:
    m.use_design(args[0], args[1])
print(f'design CLEAR {m.HH.CLEAR} SQUEEZE {m.HH.SQUEEZE}')
for ph in np.arange(0, 0.2, 0.025):
    line = f'phase {ph:.3f}:'
    for d in (-0.05, 0.0, 0.15):
        M = m.model_P(d, phase=ph)
        arm, lip = m.gate_pieces(M)
        W = arm.distance(lip); bore = M.distance(m.Point(0, 0))
        line += f' | delta {d:+.2f} throat {W:.3f} sq@6.4 {6.4 - W:+.3f} seat clr {bore - 3.2:.3f}'
    print(line)
