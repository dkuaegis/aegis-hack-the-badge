# Hacking Badge Ver.3 Manufacturing Package

This directory is the final revision 3 JLCPCB upload package.

## Upload These Files

| JLCPCB step | File |
| --- | --- |
| PCB fabrication | `upload/hacking_badge_v3_jlcpcb_gerbers.zip` |
| PCBA BOM | `upload/hacking_badge_v3_jlcpcb_bom.csv` |
| PCBA CPL | `upload/hacking_badge_v3_jlcpcb_cpl.csv` |

Recommended order options:

- Quantity: 5
- Layers: 2
- PCB thickness: 1.6 mm
- Solder mask: black
- Silkscreen: white
- PCBA: top side SMT only; `OLED1` is excluded and hand-soldered afterward

## Package Contents

- `upload/`: the three files uploaded directly to JLCPCB.
- `fabrication/gerber/`: uncompressed Gerber, drill, drill-map, and Gerber job files.
- `fabrication/hacking_badge_v3.ipc`: IPC-2581 exchange export.
- `assembly/hacking_badge_v3_assembly.glb`: complete visual assembly model.
- `assembly/hacking_badge_v3_assembly.step`: mechanical assembly export. The custom OLED
  VRML model may not be embedded in this STEP; use the GLB or PNG previews for
  complete visual review.
- `preview/`: top, bottom, and isometric KiCad renders.
- `reports/`: DRC, drill, board statistics, JLCDFM disposition, and automated
  package validation.
- `assembly/hacking_badge_v3_manual_assembly.csv`: locally sourced parts that are not
  uploaded to JLCPCB.

## Verified State

- KiCad electrical DRC: 0 errors and 0 unconnected items. Two source-layout
  warnings remain on the board-scale rear logo by design; the production
  Gerbers subtract solder-mask openings from silkscreen before plotting.
- JLCDFM hardening: 0.20/0.25 mm via drills, at least 0.20 mm via annular
  rings, 0.80 mm USB-C plated slots, 0.15 mm minimum silkscreen strokes,
  0.05 mm global solder-mask expansion, and 0.13 mm minimum mask web.
- Gerber ZIP: exact 12-file fabrication set.
- Board: 2 layers, 1.6 mm, approximately 84.05 x 100.05 mm.
- Assembly: 15 grouped BOM lines and 44 unique top-side placements.
- Buzzer circuit populated: SMD5020-ZK, AO3400A, 1N4148W, gate resistors, and
  local 10 uF capacitor.
- OLED installed manually after PCBA: locally sourced HS96L03W2C03, white
  0.96 inch 128x64 SSD1315 I2C module. The manual list recommends six modules
  for five boards so one spare is available.
- Game controls populated: `<-` on GPIO9, `OK` on GPIO10, and `->` on GPIO12.
- Front logo reproduces the complete circular source logo. Its original white
  regions print on F.SilkS and its black regions show through as black PCB.
- The front sponsor mark appears inside the left-center F.SilkS guide area as
  `Sponsored by`, `EasyEDA`, and `JLCPCB`; the previous lower-left JLCPCB-only
  mark was removed and the decorative border there was restored.
- Rear Aegis silhouette is filled with white B.SilkS at board scale. The
  30 mm MSG CTF mark is negative space that exposes the black solder mask.
- Rear staff testpoints and their labels are shifted 4 mm downward, clear of the
  logo artwork, and their local routes were revalidated after the move.

The detailed disposition of every item in the supplied PCB and SMT DFM reports
is recorded in `reports/jlcdfm_resolution.md`.

## Order Review

The CPL uses KiCad's manufacturing coordinate system, matching the Gerber and
official KiCad position export: X is unchanged and all top-side Y coordinates
are negative. The package validator rejects a CPL generated with the PCB
editor's downward-positive Y axis.

The CPL also contains verified per-package placement corrections for J1
(`C165948`), U1 (`C2913201`), U2 (`C6186`), D1 (`C2827654`), and Q_BZ
(`C20917`). The affected LCSC/EasyEDA origins or rotations do not coincide with
the KiCad footprint anchors. Do not replace these rows with the uncorrected
KiCad position-export values.

When JLCPCB shows the reminder `The system detects component that may be
offset from the PCB, does it try to automatically align it?`, select `Cancel`.
The custom shield outline and the intentional USB-C edge overhang can trigger
this false positive. Selecting `Ok` can translate or mirror the complete
placement set away from the PCB. If that happens, upload the original BOM and
CPL again; do not manually drag the scattered components into place.

Before payment, inspect every polarized or pin-1-sensitive part in the JLCPCB
placement preview, especially `U1`, `J1`, `D1`, `D_BZ`, `Q_BZ`, all LEDs, and
the tactile switches. Recheck LCSC stock because availability and PCBA class
can change.

The similar USB-C STEP model in the KiCad 3D view is visualization-only. The
fabrication footprint and BOM selection remain TYPE-C-31-M-12 (`C165948`).

The OLED module is excluded from both JLCPCB upload files. After PCBA, install
it on the front with pin order `GND, VCC, SCL, SDA` and connect VCC only to
3.3 V. The footprint uses 2.0 mm pads with a 1.1 mm nominal PTH drill for practical
hand soldering. If the module is supplied without pins, use a straight 1x4
2.54 mm male header.
