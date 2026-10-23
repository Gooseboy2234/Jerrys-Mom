"""Shared numbers for the 10% bigger access hatch (roof opening + hatch plate).

Roof-file frame (X along the roof, Y toward the hinges, Z up from the roof underside).
Ethan's opening: a 78 x 44 through-hole (Z 0-1.2) with an 80 x 46 rebate on top (Z 1.2-2.4)
that the 1.2 mm hatch plate sits in, plus a 5 mm finger notch in front.

Both parts are scaled in the plane by S about the opening centre. Thickness is not scaled
(the rebate is 1.2 deep and the plate is 1.2 thick). A 10% growth does not fit in Y exactly:
the raised screen frame ends at Y 63.0 and the hinge bases start at Y 116.88, so the opening
is nudged (SHIFT) and the notch is kept at its old size.
"""
import numpy as np

S = 1.10
CENTER = (47.0, 92.0)           # centre of the old rebate
SHIFT = (-1.0, -0.7)            # x: keep 1.5 mm of wall to the vent field; y: fit between frame and hinge base

OLD_HOLE = dict(x=(8.0, 86.0), y=(70.0, 114.0), z=(0.0, 1.2))
OLD_REBATE = dict(x=(7.0, 87.0), y=(69.0, 115.0), z=(1.2, 2.4))
OLD_NOTCH = dict(c=(47.0, 68.3), r=2.5)
PLATE_Z = (0.0, 2.4)

HATCH_TO_ROOF = dict(x0=7.2, y0=68.9, z0=-1.65)   # hatch (x thick, y wide, z long) -> roof (X = x0+z, Y = y0+y, Z = z0+x)


def scale_xy(v, s=S):
    """The in-plane map A applied to a roof-frame (X, Y)."""
    return (CENTER[0] + (v[0] - CENTER[0]) * s + SHIFT[0], CENTER[1] + (v[1] - CENTER[1]) * s + SHIFT[1])


def new_box(b):
    (x0, x1), (y0, y1) = b['x'], b['y']
    a, c = scale_xy((x0, y0)), scale_xy((x1, y1))
    return dict(x=(a[0], c[0]), y=(a[1], c[1]), z=b['z'])


NEW_HOLE = new_box(OLD_HOLE)
NEW_REBATE = new_box(OLD_REBATE)
# the notch keeps its size and sits 0.2 in front of the new rebate front edge
NEW_NOTCH = dict(c=(CENTER[0] + SHIFT[0], NEW_REBATE['y'][0] - 0.2), r=2.5)


def T():
    """hatch frame -> roof frame (4x4)."""
    p = HATCH_TO_ROOF
    return np.array([[0, 0, 1, p['x0']], [0, 1, 0, p['y0']], [1, 0, 0, p['z0']], [0, 0, 0, 1.0]])


def A():
    """roof frame in-plane scale map (4x4), Z unchanged."""
    M = np.eye(4)
    M[0, 0] = M[1, 1] = S
    M[0, 3] = CENTER[0] - S * CENTER[0] + SHIFT[0]
    M[1, 3] = CENTER[1] - S * CENTER[1] + SHIFT[1]
    return M


def B():
    """hatch frame -> hatch frame: scale the hatch exactly as the opening is scaled."""
    return np.linalg.inv(T()) @ A() @ T()
