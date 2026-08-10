# Hacking Badge Ver.3 KiCad Project

This directory contains the routed production PCB, connected review
schematic, project-local symbols and footprints, 3D assets, and electrical
verification reports for the ESP32-S3 Hacking Badge Ver.3.

## Directory Layout

- Project root: editable KiCad project and local libraries only.
- `scripts/`: deterministic generation and validation scripts.
- `reports/`: current DRC, ERC, netlist, and validation reports.
- `exports/`: current human-readable schematic and 3D PDF exports.
- Historical PCB revisions, autorouter sessions, rescue files, and superseded
  renders live in `../../../../archive/design/rev3-development/` and are not
  used for production.

## Main Design Files

- `hacking_box_v2.kicad_sch`: connected one-page A3 production schematic.
- `hacking_box_v2.kicad_pcb`: routed two-layer production PCB.
- `hacking_box_v2.kicad_pro`: KiCad project settings.
- `exports/hacking_box_v2_schematic.pdf`: printable schematic.
- `hacking_box_v2-cache.lib`: project-local legacy symbol source.
- `sym-lib-table`: local symbol-library registration.
- `hacking_box_v2.pretty/`: local buzzer and OLED footprints.
- `hacking_box_v2.3dshapes/`: local OLED 3D model.
- `../reference/datasheets/HS96L03W2C03.pdf`: source module datasheet used for the
  OLED outline, mounting holes, pin order, and hand-solder pad review.

The notes-only schematic that preceded the connected capture is archived at
`../../../../archive/design/rev3-development/pcb-revisions/hacking_box_v2_notes_only_2026-07-28.kicad_sch`.

## Schematic Organization

The A3 sheet groups USB-C and power, ESP32-S3, OLED, five status LEDs, three
game controls, challenge pads, player UART, rear staff testpoints, and the
buzzer driver. Global net labels make each PCB net explicit without long
cross-sheet wires.

The schematic was reverse-captured from the finished PCB. It is electrically
equivalent to the PCB, but this revision did not originate through KiCad's
normal schematic-first association flow. Review symbol-footprint associations
before using **Update PCB from Schematic**.

## Verification

- Schematic ERC: 0 errors, 0 warnings.
- Schematic-to-PCB validation: PASS.
- Components: 60 in schematic and PCB.
- Named nets: 37 in schematic and PCB.
- Connected component-pin pairs: 149.
- Intentional no-connect pins: 20.
- PCB DRC: 0 error-level violations and 0 unconnected items.

Reports:

- `reports/erc-final.rpt`
- `reports/schematic-pcb-validation.txt`
- `reports/drc_report_jlcdfm_fixes.txt`

## Regeneration

Run `scripts/generate_production_schematic.py` with KiCad's bundled Python to
recreate the legacy capture and local symbol library from PCB pad/net data.
Open the generated `hacking_box_v2.sch` in KiCad and save it to refresh the
modern `.kicad_sch`.

Run `scripts/add_jlcpcb_sponsor_logo.py` with KiCad's bundled Python to rebuild
the front `Sponsored by` EasyEDA/JLCPCB sponsor mark in the left-center
silkscreen area. The script groups the generated logo polygons and restores the
lower-left decorative border that was previously interrupted by the old
JLCPCB-only mark.

Export an XML netlist, then run
`scripts/validate_schematic_against_pcb.py` with KiCad's bundled Python. The
validator compares references, values, named pin-to-net mappings, and
intentional no-connect pins.

## Manufacturing

The order artifacts are in `hardware/releases/rev3/jlcpcb/`; the three files
uploaded to JLCPCB are isolated in its `upload/` directory. `OLED1` is excluded
from the JLCPCB BOM/CPL and appears in `assembly/` as a separate manual list. Its
footprint uses 2.0 mm pads with a 1.1 mm nominal PTH drill for hand soldering.
The Gerber, drill, BOM, CPL, and validation reports were regenerated after
this change and the supplied JLCDFM findings. The final fabrication package
uses 0.80 mm plated USB-C slots, 0.20 mm minimum drills, 0.15 mm minimum
silkscreen strokes, and mask-subtracted silkscreen output.
