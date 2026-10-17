"""Shaded renders of the closed case, original vs revised."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from assemble import assembly, W, D

H = os.path.dirname(os.path.abspath(__file__))
COLORS = {"floor": (0.30, 0.62, 0.36)}
PURPLE = (0.48, 0.30, 0.70)
LIGHT = np.array([-0.4, -0.7, 0.9]); LIGHT /= np.linalg.norm(LIGHT)


def draw(ax, parts, elev, azim, lims):
    for k, m in parts.items():
        tri = m.triangles
        shade = 0.35 + 0.65 * np.clip(m.face_normals @ LIGHT, 0, 1)
        base = np.array(COLORS.get(k, PURPLE))
        fc = np.clip(base[None, :] * shade[:, None] * 1.25, 0, 1)
        ax.add_collection3d(Poly3DCollection(tri, facecolors=fc, edgecolors="none", linewidths=0))
    ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1]); ax.set_zlim(*lims[2])
    ax.set_box_aspect([lims[0][1] - lims[0][0], lims[1][1] - lims[1][0], lims[2][1] - lims[2][0]])
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()


views = [
    ("whole box, front-left", 22, -125, [(-5, W + 5), (-5, D + 8), (-4, 84)]),
    ("front-left corner", 18, -130, [(-3, 45), (-4, 40), (30, 84)]),
    ("front-right corner (port)", 15, -60, [(120, W + 3), (-4, 40), (0, 50)]),
]
O, R = assembly("original"), assembly("revised")
fig = plt.figure(figsize=(18, 11))
for i, (title, el, az, lims) in enumerate(views):
    for j, (parts, name) in enumerate(((O, "Before"), (R, "After"))):
        ax = fig.add_subplot(2, 3, 1 + i + 3 * j, projection="3d")
        draw(ax, parts, el, az, lims)
        ax.set_title(f"{name}: {title}", fontsize=11)
plt.tight_layout()
out = os.path.join(H, "..", "renders", "case_before_after.png")
plt.savefig(out, dpi=90)
print(out)
