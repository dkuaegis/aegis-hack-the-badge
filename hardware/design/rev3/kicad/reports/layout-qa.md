# Hacking Badge Ver.3 Design QA

Date: 2026-08-02

## PCB Status

- Aegis shield outline: approximately 84.05 x 100.05 mm.
- Stackup: two copper layers, 1.6 mm FR-4.
- Footprints: 60 total, 51 front and 9 rear.
- Routed tracks/vias: 577 board track items.
- Copper zones: 11.
- KiCad error-level DRC: 0 violations.
- Unconnected board items: 0.
- ESP32 antenna keep-out: implemented at the right board edge.
- OLED: `HS96L03W2C03`, four-pin `GND, VCC, SCL, SDA` module; datasheet body
  and mounting pattern retained, with 2.0 mm/1.1 mm hand-solder header pads.
- Production exports: Gerbers, drill, BOM, and CPL validated in
  `hardware/releases/rev3/jlcpcb/`.
- JLCPCB assembly set: 15 grouped BOM lines and 44 top-side placements.
- Manual assembly set: `OLED1` only, one per board.

## Schematic Status

- Connected A3 KiCad schematic generated from the production PCB.
- Functional blocks: USB/power, controller, OLED, status LEDs, controls,
  challenge outputs, UART, testpoints, and buzzer.
- KiCad ERC: 0 errors, 0 warnings.
- PCB/schematic component references: 60/60, exact match.
- PCB/schematic named nets: 37/37, exact match.
- Connected component-pin pairs: 149, exact match.
- Intentional no-connect pins: 20, exact match.
- PDF render inspected after grid and net-label direction corrections.

## Final DRC

- KiCad DRC: 0 errors and 0 unconnected items.
- Remaining source warnings: two intentional clearances from the board-scale
  rear silkscreen logo. Production Gerbers subtract mask openings from silk.
- JLCDFM geometry: 0.20/0.25 mm via drills, 0.20 mm annular rings, 0.80 mm
  plated USB-C slots, and at least 0.15 mm plotted silkscreen strokes.
- Report: `drc_report_jlcdfm_fixes.txt`.

## Workflow Note

The PCB remains the Rev.3 manufacturing source of truth. The schematic is an
electrically exact reverse capture, verified by
`scripts/validate_schematic_against_pcb.py`, but symbol-footprint associations
must be reviewed before pushing schematic changes back into the PCB.
