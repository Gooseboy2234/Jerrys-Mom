# Tanki purple case — revision 1 (bevels + vents)

Changes from Ethan's current build (R2 walls/lid/hinges + R3 roof):

1. **Roof vents moved 20 mm back** (toward the hinges), with all 113 Tanki icon cutouts kept.
   20 mm is as far as they can go before hitting the right hinge base (1.9 mm left).
2. **4 mm 45° bevels** on all four vertical corners, from the floor up through the walls,
   roof and lid. The lid's front, left and right top edges are beveled too; the hinge edge
   stays square so the hinges and their 105° stop are untouched.
3. **Front USB/Ethernet opening moved 3.2 mm left** (now X 93.8–161.8) so the
   front-right corner bevel stays solid. The Pi now sits further back.

## Files (`revised/`, kept out of git)

| Part | File | Notes |
|---|---|---|
| Roof (R3) | `02_R3_top_vents_back_20mm_bevel4` | Vents moved + corner bevels. Replaces the R3 roof. |
| 7" lid | `01_7in_lid_bevel4` | Corner and top-edge bevels, plus ~1.5 cm³ of reinforcement inside so the 1.2 mm rims don't open up |
| Front wall | `03_Front_wall_bevel4_port_left3.2` | End bevels, port moved, small reinforcing blocks inside the corners |
| Rear wall | `04_Rear_wall_bevel4` | End bevels + inside corner blocks |
| Left / right walls | `05_Left_wall_bevel4`, `06_Right_wall_bevel4` | Only change: a 1.6 mm 45° sliver off the **outer** vertical edge at each end. Reprint, **or sand the glued walls in place**. |
| Floor | `Green_toast_bottom_bevel4` | 4 mm corner bevels. Reprint, **or sand/cut the corners** of the existing floor. |
| Everything else | unchanged | Hatch, bearing caps, tab keepers, bumper, feet, antenna holder, riser |

Every revised file is a single closed body with no bad triangles, fits the A1 mini bed and
keeps its original print orientation. The assembled box was checked in `tools/assemble.py`:
nothing pokes outside the beveled outline and no two parts overlap.

## Things to check on the real build

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
`move_roof_vents.py`, then `bevel_case.py`. `assemble.py` places the parts in the case
frame, and `stlcheck.py` runs the mesh checks. Needs `trimesh manifold3d shapely networkx`.
