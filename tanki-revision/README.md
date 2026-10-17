# Tanki purple case — revision 1 (bevels + vents)

Changes from Ethan's current build (R2 walls/lid/hinges + R3 roof):

1. **Roof vents moved 20 mm back** (toward the hinges), with all 113 Tanki icon cutouts kept.
   20 mm is as far as they can go before hitting the right hinge base (1.9 mm left).
2. **4 mm 45° bevels** on all four vertical corners, from the floor up through the walls,
   roof and lid. The lid's front, left and right top edges are beveled too; the hinge edge
   stays square so the hinges and their 105° stop are untouched.
3. **Screen opens to 120° instead of 106°.** The lid's centre hinge tab lands on a small
   stop block on each roof hinge base. Both blocks moved 2.1 mm forward
   (`tools/hinge_stop.py <angle>` re-runs it). Keep it under ~125°: past that the lid's
   rear edge reaches the back of the hinge seats.
4. **Lift-off hook hinge, no caps.** Each of the roof's four U-seats is now a 3 mm-thick hook
   that curls over the top of the lid's pivot. It opens forward and 15° up, through a 6.15 mm
   gap (the pivot is 6.4 mm) set by a small bump on the lip. The pivot clicks past the bump
   going in and out. Lifting straight up, pushing back (the stop load) and the lid's weight
   are all blocked. The four bearing caps are no longer used. To remove the lid, hold it
   between closed and ~40° open and pull it toward you and slightly up.
   (`tools/hinge_hook.py [exit_deg]`, `tools/hook_2d.py` checks the click.)
5. **Front USB/Ethernet opening moved 3.2 mm left** (now X 93.8–161.8) so the
   front-right corner bevel stays solid. The Pi now sits further back.

## Files (`revised/`, kept out of git)

| Part | File | Notes |
|---|---|---|
| Roof (R3) | `02_R3_top_vents_back_20mm_bevel4_open120_hook15` | **Print this one.** Vents moved, corner bevels, 120° stop, lift-off hook seats. Replaces the R3 roof. The hooks overhang the pivot, so print with supports (the R3 project already uses tree supports). Earlier steps are kept: `..._open120` (glued caps), `..._bevel4` (106° stop). |
| Hinge test pair | `TEST_hinge_hook_roof_coupon`, `TEST_hinge_hook_lid_coupon` | One hinge cut from the roof and lid (~11 g total). **Print these first** to check the click, the 120° stop and lift-out before the 3-hour roof. Use a brim on the lid piece; it stands 29 mm tall on a small footprint. |
| 7" lid | `01_7in_lid_bevel4` | Corner and top-edge bevels, plus ~1.5 cm³ of reinforcement inside so the 1.2 mm rims don't open up |
| Front wall | `03_Front_wall_bevel4_port_left3.2` | End bevels, port moved, small reinforcing blocks inside the corners. **Prints flat**. |
| Rear wall | `04_Rear_wall_bevel4` | End bevels + inside corner blocks. **Prints flat**. |
| Left / right walls | `05_Left_wall_bevel4`, `06_Right_wall_bevel4` | Only change: a 1.6 mm 45° sliver off the **outer** vertical edge at each end. Reprint, **or sand the glued walls in place**. |
| Floor | `Green_toast_bottom_bevel4` | 4 mm corner bevels. Reprint, **or sand/cut the corners** of the existing floor. |
| Bearing caps (07-10) | **not needed** with the hook roof | |
| Everything else | unchanged | Hatch, tab keepers, bumper, feet, antenna holder, riser |

Every revised file is a single closed body with no bad triangles and fits the A1 mini bed.
All four walls print **flat**. The front and rear walls go outer face down with the corner blocks
pointing up, so the only overhangs are the 45° end bevels (about 350 mm² vs ~2,100 mm² standing up).
The side walls keep Ethan's flat orientation (outer face up, no overhangs).
Every other part keeps its original print orientation. The assembled box was checked in `tools/assemble.py`:
nothing pokes outside the beveled outline and no two parts overlap.

## Things to check on the real build

- **Hook click (test pair first).** The 0.25 mm squeeze is a starting point. If it's too stiff
  in PLA (or cracks), re-run with less: change `SQUEEZE` in `hinge_hook.py`. PETG flexes better.
  With the lid closed, nothing but the click stops it sliding forward out of the hooks.

- **Tipping at 120°.** With the screen open, the lid's weight sits about 28 mm behind the
  rear edge. The box only tips back if the lid outweighs the base by about 2.7x
  (estimated with a 200 g display), so it should be fine.

- **Front-left inside corner.** The new block stays at X ≤ 3.6, 0.3 mm short of the
  nominal edge of the glued screen/riser (X 3.9). If yours sits closer to the left wall, trim the block.
- **Rear-right inside corner.** Each wall corner gets a small block (about 1.8 × 2.6 mm,
  full height). Since the Pi moved back, make sure its bumper clears that corner.
- **Floor Pi cutout.** The green floor has a cutout at X 140–155, Y 55–102 under the Pi.
  If the Pi moved back, that may need to move too.
- **Lid / display.** The display board position is inferred from the standoff spacing
  (156.9 × 114.96) and the nominal board size (164.9 × 124.27). At the rear corners its
  corners sit about 0.15 mm inside the bevel. Measure your display before printing the lid.
- **Wall orientation** was worked out from the vent icons (they only match the roof's
  icons from one side). If the left wall's recessed panels face outward on your build,
  that confirms it.

## Tools

`tools/` regenerates everything from Ethan's originals in `original/`:
`move_roof_vents.py`, then `bevel_case.py`, then `hinge_stop.py 120`. `hinge_sweep.py` rotates
the lid about its pivot axis (case Y 142.884, Z 70.0) to find the angle where it first touches anything. `assemble.py` places the parts in the case
frame, and `stlcheck.py` runs the mesh checks. Needs `trimesh manifold3d shapely networkx`.
