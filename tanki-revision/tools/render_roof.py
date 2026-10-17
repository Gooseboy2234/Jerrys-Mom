"""Top-view before/after of the roof vent move."""
import os, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import trimesh
from matplotlib.patches import Rectangle
H = os.path.dirname(os.path.abspath(__file__))
pairs = [("original/02_R3_corrected_reinforced_top_-_print_ONE.stl", "Before"),
         ("revised/02_R3_top_vents_back_20mm_-_print_ONE.stl", "After: vents 20 mm back")]
fig, axs = plt.subplots(1, 2, figsize=(14, 7))
for ax, (p, title) in zip(axs, pairs):
    m = trimesh.load(os.path.join(H, "..", p))
    for z, c, lw in ((1.2, "#5b2a86", .7), (4.6, "#b07cd8", .9)):
        for loop in m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]).discrete:
            ax.plot(loop[:, 0], loop[:, 1] - 2, color=c, lw=lw)
    ax.add_patch(Rectangle((0, 0), 167.4, 146.88, fill=False, ls="--", color="grey", lw=.8))
    ax.annotate("FRONT (USB/Ethernet wall)", (83.7, -9), ha="center", fontsize=9)
    ax.annotate("REAR (hinges)", (83.7, 152), ha="center", fontsize=9)
    ax.set_title(title); ax.set_aspect("equal"); ax.set_xlim(-8, 176); ax.set_ylim(-14, 158); ax.axis("off")
plt.tight_layout(); plt.savefig(os.path.join(H, "..", "renders", "roof_vents_before_after.png"), dpi=110)
