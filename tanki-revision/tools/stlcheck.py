import sys, struct, hashlib, os
import numpy as np

BED = 180.0
PLA = 1.24  # g/cm^3


def load(path):
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    if 84 + 50 * n == len(data):
        rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
        return rec["v"].astype(np.float64), "binary"
    tris = []
    cur = []
    for line in data.decode("ascii", "replace").splitlines():
        p = line.split()
        if p and p[0] == "vertex":
            cur.append([float(x) for x in p[1:4]])
            if len(cur) == 3:
                tris.append(cur)
                cur = []
    return np.array(tris, dtype=np.float64), "ascii"


def analyse(path):
    t, fmt = load(path)
    lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
    size = hi - lo
    cross = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2
    degenerate = int((area < 1e-9).sum())
    vol = float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)
    # edge manifold check: each undirected edge shared by exactly 2 faces, opposite directions
    q = np.round(t, 5)
    flat = q.reshape(-1, 3)
    _, vid = np.unique(flat, axis=0, return_inverse=True)
    f = vid.reshape(-1, 3)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    und = np.sort(e, axis=1)
    _, inv, cnt = np.unique(und, axis=0, return_inverse=True, return_counts=True)
    bad_edges = int((cnt != 2).sum())
    # orientation: for edges used twice, directions should be opposite
    fwd = (e[:, 0] < e[:, 1]).astype(int)
    s = np.zeros(len(cnt)); np.add.at(s, inv.ravel(), fwd)
    misoriented = int(((cnt == 2) & (s != 1)).sum())
    # connected bodies via union-find on vertices
    parent = np.arange(vid.max() + 1)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in und:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    bodies = len({find(v) for v in np.unique(f)})
    fits = all(size[:2] <= BED) and size[2] <= BED
    return dict(fmt=fmt, tris=len(t), lo=lo, hi=hi, size=size, vol_cm3=vol / 1000, mass_solid_g=abs(vol) / 1000 * PLA,
                degenerate=degenerate, open_or_nonmanifold_edges=bad_edges, misoriented_edges=misoriented,
                bodies=bodies, fits_bed=fits, sha256=hashlib.sha256(open(path, "rb").read()).hexdigest()[:16])


for p in sys.argv[1:]:
    r = analyse(p)
    name = os.path.basename(p)
    print(f"== {name}")
    print(f"   {r['fmt']}, {r['tris']} tris, sha256 {r['sha256']}…")
    print("   size  X {:.3f}  Y {:.3f}  Z {:.3f} mm   (min {} )".format(*r["size"], np.round(r["lo"], 3)))
    print(f"   volume {r['vol_cm3']:.2f} cm3, solid PLA ≈ {r['mass_solid_g']:.1f} g")
    print(f"   bodies {r['bodies']}, degenerate {r['degenerate']}, open/non-manifold edges {r['open_or_nonmanifold_edges']}, misoriented {r['misoriented_edges']}, fits 180 bed: {r['fits_bed']}")
