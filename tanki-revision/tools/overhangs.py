"""Overhang report: downward-facing area not on the bed, per orientation."""
import sys, numpy as np, trimesh

def report(tm, label=""):
    n = tm.face_normals; a = tm.area_faces
    zc = tm.triangles_center[:, 2] - tm.bounds[0, 2]
    down = n[:, 2] < -np.cos(np.radians(45)) + 1e-6   # steeper than 45 deg from vertical
    off_bed = zc > 0.05
    oh = a[down & off_bed].sum()
    return f"{label:42s} size {np.round(tm.extents, 1).tolist()}  overhang>45deg {oh:7.1f} mm2  bed contact {a[(n[:, 2] < -0.99) & ~off_bed].sum():8.1f} mm2"

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(report(trimesh.load(p), p.split("/")[-1][:42]))
