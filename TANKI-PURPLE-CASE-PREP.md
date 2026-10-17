# Tanki purple case — prep checklist

From Ethan's handoff email (fungoose41@gmail.com, 16 Oct 2026).

## 1. Get the files (you have to do this, signed in as danefane7@gmail.com)
- [ ] ZIP A — parts, editable sources, print projects (94.4 MB):
      https://drive.google.com/file/d/13RwN8OSZAJyhNkxXaMdhdbE_6b87f80e/view
- [ ] ZIP B — guides, pictures, Blender assembly steps (71.7 MB):
      https://drive.google.com/file/d/163mtMzXFnN6wKIU8R1jU-uFC2QpQsAy2/view
- [ ] Extract both to the same place and merge the shared top-level folder
- [ ] Check `SHA256SUMS.txt` before changing anything

## 2. Read first
- [ ] `START HERE - All parts.md`
- [ ] `DANE - FULL DESIGN HANDOFF.md`
- [ ] PDF in `02 - Assembly guides and pictures/Extended R2 guide`
      (its small-screen corner is out of date, so use the R3 pictures for that corner)

## 3. The big rule
Current build = **R2 walls/lid/hinges + corrected R3 roof**.
Print **only** `01 - Individual STLs`: 23 files, one of each.
Do **not** print folder 04, the original R2 batch with the old roof.
Folder 05 holds test coupons and alternates. None of them are required parts.

| Color  | Qty | Parts |
|--------|-----|-------|
| Purple | 15  | 7" backplate/lid, R3 top (with hinge bases), 4 walls, 4 bearing caps, 2 bottom + 2 top display-tab keepers, service hatch |
| Black  | 6   | Orange Pi edge bumper, 4 × 5mm feet, 5mm rod antenna holder |
| Grey   | 1   | ESP-screen riser (86×50 base, 50.8mm tall) |
| Green  | 1   | Toast CENTER floor (167.4 × 146.88 × 2.8mm) |

### STL check (17 Oct 2026): all 23 files uploaded
Every file is one closed body with no bad triangles, and every file fits the 180mm bed.

- R3 top 167.4 × 150.4 × 16.2. Window 72.4 × 53.2 at X 46.9 / Y 27.4.
  The file adds a 2mm front lip, so its Y origin sits 2mm forward of the case.
  Four 3.4mm holes, 78 × 42 apart, which lines up with the riser posts.
  The webs between the holes and the window are 1.1mm.
- Walls: front/rear 167.4 × 2.4 × 53.8 (print standing up), left/right 142.08 × 53.8 × 2.4 (print flat).
- Riser: 2.4 base + 50.8 posts + 2mm tips. Posts 78 × 42 apart.
- Identical copies: 4 bearing caps, 4 feet, 2 bottom keepers, 2 top keepers.
  The **top and bottom keepers differ** (10.75 vs 10.45mm), so label them.
- Tall prints: the backplate is 167.4mm tall upright and the hatch is 79.6mm tall on its edge.
  Use a brim and the supplied orientations.
- A fully solid set would weigh about 330 g. Real prints with infill will be lighter.

## 4. Before printing the full R3 roof
- [ ] Measure the already-glued small screen and the wall datums
- [ ] Print the R3 corner coupon (~42 min, 8.5 g) and test-fit it
- [ ] Don't force the cover onto the glass or bend the PCB

## 5. Printer settings
Bambu A1 mini, PLA, 0.4mm nozzle, 100% scale, keep the supplied orientations.
Use each part's own README or native project instead of one setting for everything.
The R3 project (folder 06) uses 20% gyroid, tree supports and a 3mm brim
(~3h04m, ~49.5 g).

## 6. Hardware to check (purchased, not printed)
Displays, Orange Pi, Noctua fan + silicone mounts, antenna/coax,
USB/HDMI/power leads, adhesive. Check cable slack and coax length.

## 7. Only if editing the design
Main scenes: R2 `Purple-compute-box-editable.blend` and R3 `R3 corrected top editable.blend`.
The generator scripts are hard-coded to `/Users/ethan/Documents/OrangePiTanki`.
Run them only on a working copy, after rebinding those paths, in Blender 4.x.
Keep the hash checks on.
