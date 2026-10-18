# Hinge lab brief: digital test of the lift-off hook hinge (Bambu A1 mini tolerances)

You are one tester on a team. Each tester owns ONE failure mode. Work in your own folder
`/home/user/Jerrys-Mom/tanki-revision/hinge-lab/<your-test-name>/` and never edit files
outside it (the design files are read-only for you).

## Tools
- Blender 4.2.3 LTS, headless: `blender -b --factory-startup --python your_script.py -- args`
  - STL import: `bpy.ops.wm.stl_import(filepath=...)`; export: `bpy.ops.wm.stl_export(filepath=..., export_selected_objects=True)`
  - Booleans: Boolean modifier with `solver='EXACT'`, then evaluate (depsgraph) to measure.
  - Overlap: `mathutils.bvhtree.BVHTree.FromBMesh` + `.overlap()`; volume: `bmesh` `calc_volume()`.
  - **Blender must be your main 3D tool** (the user asked for Blender). You may also use
    Python 3 with numpy/trimesh/manifold3d/shapely for 2D sections and numeric checks.
- Smoke test that works: `hinge-lab/smoke.py`.

## Geometry (all files in the assembled CASE frame, mm)
Case frame: X = left→right (along the hinge axis), Y = front→rear (toward the hinges),
Z = up, floor top = 0. The roof underside is at Z 53.8.
- `hinge-lab/roof_left_hinge_case.stl`: roof cropped around the LEFT hinge (X 24–60). It has two hook
  seats (X 30–36.7 and 47.3–54) and, between them, the stop block (X 38.2–45.8).
- `hinge-lab/lid_left_hinge_case_closed.stl`: the lid cropped around the same hinge, CLOSED (0°).
  Its two round pivots (Ø6.4, r 3.2) sit in the hooks; its centre knuckle has the stop tab.
- `hinge-lab/roof_full_case.stl`, `hinge-lab/lid_full_case_closed.stl`: full parts (the right hinge is a
  copy at X 113.4–137.4).
- **Pivot axis:** the line parallel to X through (Y 142.884, Z 70.0). The lid opens by rotating about
  it by −θ around +X (the front edge rises), i.e. `Matrix.Rotation(-θ, 4, 'X')` about that point.
  0° = closed; the design stop is 120°.
- Hook design (`tools/hinge_hook.py`): seat inner radius 3.5 (0.3 radial clearance), 3 mm wall.
  The opening ("throat") faces EXIT = 165° in the Y-Z plane (0° = +Y rear, 90° = +Z up,
  180° = −Y front), i.e. forward and 15° up. The throat is between the arm tip, which curls over
  the top to ~105°, and a Ø1.2 bump on the lower front lip, centred about 4.09 from the axis at
  ~229°. The throat is 6.15 wide: 0.25 squeeze for the 6.4 pivot (the "click"). Seated, the bump
  clears the pivot by 0.27–0.30.
- Stop: the lid tab lands on a block on the roof at 120°. Without the block, the next contact is
  ~126° (lid rear edge vs the back of the seats).
- Verified nominally (no tolerances): free swing 0–119°, stop at 120°; lift-out only near 165° with
  the click; clean lift-out with the lid between closed and ~40° open.

## Print reality (Bambu A1 mini, 0.4 mm nozzle, PLA, 0.20 mm layers, Bambu Studio defaults)
Use these as RANGES and test the extremes, not just the middle:
- **Roof** prints flat: print XY = case X/Y, print Z = case Z − 53.8. So the hook profile (case Y-Z
  plane) is layer-stepped in Z (0.20 layers; the slicer takes each layer's section at mid-layer
  and extrudes it). The first layer is 0.20.
- **Lid** prints upright (print Z = case X), so its pivots print as vertical cylinders: round in XY,
  no stepping.
- XY dimensional error per surface: −0.05 to +0.15 mm outward (outer walls/convex parts grow;
  holes and concave seats shrink by the same amount).
- Small vertical cylinders (the lid pivots): diameter −0.05 to +0.20, including a seam blob of up to
  +0.2 on one side.
- Support: Bambu default top Z distance 0.20. Surfaces printed onto supports (downward-facing
  overhangs: the underside of the hook arm over the pivot) can sag or roughen 0.10–0.30 toward
  the support. Unsupported 45–60° overhangs droop ~0.05–0.15.
- Elephant foot 0.10–0.20 (first layers only). Positional repeatability ±0.05.
- Materials: PLA E ≈ 3.0–3.5 GPa, strength along lines ~45–55 MPa, between layers ~20–30 MPa,
  elongation at break ~3–5%. PETG E ≈ 2.0 GPa, more ductile.
- Lid mass with display: 0.21–0.34 kg. The hinge swings freely, so the lid drops onto the stop.

## Pass criteria (use these unless you justify better ones)
- Seated pivot keeps ≥ 0.05 mm radial clearance everywhere in the 0–120° swing (it turns freely; no binding).
- Click squeeze between 0.10 and 0.45 mm (it clicks but doesn't jam or crack). Below 0.10 = no click,
  above 0.45 = too hard / risks cracking.
- Lifting straight up, pushing back and down (weight) stay blocked by ≥ 0.5 mm of interference.
- Stop between 116° and 124°; never reaches the ~126° secondary contact.
- Printable on the A1 mini with sane supports; minimum walls ≥ 0.8 mm (2 lines).

Report numbers. If something fails, say which tolerance corner breaks it and propose the
smallest parameter change in `tools/hinge_hook.py` (SQUEEZE, CLEAR, WALL, BUMP_R, EXIT) or
`tools/hinge_stop.py` that fixes it.
