"""Place each printed part in the case frame (X toward the Pi, Y toward hinges, Z up,
floor top = 0) so the closed box can be checked and rendered.

Orientation evidence: wall outer faces come from the vent icons, which read correctly
(match the roof's icons) only from one side; the roof matches the handoff's window
coordinates with a 2 mm forward lip; the lid is the only proper rotation that puts its
hinge knuckles over the roof's hinge bases with the display facing down when closed.
"""
import os
import numpy as np
import trimesh

H = os.path.dirname(os.path.abspath(__file__))
W, D, T, WALL_H = 167.4, 146.883789, 2.4, 53.8
LID_TOP = WALL_H + 2.4 + 25.8


def M(rows, t):
    m = np.eye(4); m[:3, :3] = np.array(rows, float); m[:3, 3] = t
    return m


PLACEMENT = {
    "floor": M([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, -2.8]),
    "front": M([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0]),
    "rear":  M([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], [W, D, 0]),
    "left":  M([[0, 0, -1], [-1, 0, 0], [0, 1, 0]], [T, D - T, 0]),
    "right": M([[0, 0, 1], [1, 0, 0], [0, 1, 0]], [W - T, T, 0]),
    "roof":  M([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, -2.0, WALL_H]),
    "lid":   M([[0, 0, -1], [1, 0, 0], [0, -1, 0]], [W, 0, LID_TOP]),
}
for k, m in PLACEMENT.items():
    assert abs(np.linalg.det(m[:3, :3]) - 1) < 1e-9, k

SETS = {
    "original": {
        "floor": "original/Green_toast_bottom_-_CENTER_original_geometry_-_print_ONE.stl",
        "front": "original/03_Front_Tanki_wall_-_print_ONE.stl",
        "rear": "original/04_Rear_Tanki_wall_-_print_ONE.stl",
        "left": "original/05_Left_Tanki_wall_-_print_ONE.stl",
        "right": "original/06_Right_Tanki_wall_-_print_ONE.stl",
        "roof": "original/02_R3_corrected_reinforced_top_-_print_ONE.stl",
        "lid": "original/01_Extended_7in_display_backplate_-_print_ONE.stl",
    },
    "revised": {
        "floor": "revised/Green_toast_bottom_bevel4_-_print_ONE.stl",
        "front": "revised/03_Front_wall_bevel4_port_left3.2_-_print_ONE.stl",
        "rear": "revised/04_Rear_wall_bevel4_-_print_ONE.stl",
        "left": "revised/05_Left_wall_bevel4_-_print_ONE.stl",
        "right": "revised/06_Right_wall_bevel4_-_print_ONE.stl",
        "roof": "revised/02_R3_top_vents_back_20mm_bevel4_-_print_ONE.stl",
        "lid": "revised/01_7in_lid_bevel4_-_print_ONE.stl",
    },
}


def assembly(which):
    parts = {}
    for k, rel in SETS[which].items():
        m = trimesh.load(os.path.join(H, "..", rel))
        m.apply_transform(PLACEMENT[k])
        parts[k] = m
    return parts
