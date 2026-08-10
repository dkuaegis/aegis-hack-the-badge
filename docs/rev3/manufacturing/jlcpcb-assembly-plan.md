# JLCPCB Assembly Plan

Status: Revision 3 production package prepared for a five-board quote.

## Order Settings

| Setting | Value |
| --- | --- |
| Quantity | 5 |
| Layers | 2 |
| Thickness | 1.6 mm |
| Solder mask | Black |
| Silkscreen | White |
| Assembly side | Top |
| OLED | Excluded from PCBA; DeviceMart `HS96L03W2C03` hand-soldered after assembly |

## Upload Files

- PCB: `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_gerbers.zip`
- BOM: `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_bom.csv`
- CPL: `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_cpl.csv`
- Manual parts list: `hardware/releases/rev3/jlcpcb/assembly/hacking_badge_v3_manual_assembly.csv`

## Assembly Scope

JLCPCB places 44 top-side references, including the ESP32-S3 module, USB-C
connector, ESD device, AMS1117 regulator, five LEDs, three game buttons, the
complete buzzer driver, and all passive support parts. `OLED1` is intentionally
excluded from both assembly uploads and is installed manually after PCBA.

## Pre-Order Review

- Confirm all 44 CPL placements are on the top side.
- Inspect USB-C, diodes, LEDs, MOSFET, ESP32-S3, and buttons for rotation/pin-1.
- Confirm `C2913201`, `C165948`, `C2827654`, `C6186`, `C49246955`, `C20917`,
  and `C917030` are available in the live parts picker.
- Confirm `OLED1` does not appear in the JLCPCB BOM, CPL, or placement preview.
- Source at least five `HS96L03W2C03` modules locally; six are recommended to
  leave one spare. Add a straight 1x4 2.54 mm male header if it is not supplied.
- Verify the ESP32 antenna end faces the board edge.
- Check black solder mask and white silkscreen in the Gerber preview.
- Confirm the rear logo is intentionally interrupted by solder-mask openings
  around pads and holes.
- Review the final quote before ordering; stock and Extended-part fees change.

## Validation

- Electrical DRC: 0 errors, 0 unconnected.
- Gerber archive: exact 12-file fabrication set.
- Stackup metadata: 2 layers, 1.6 mm.
- Board profile: approximately 84.05 x 100.05 mm.
- BOM/CPL reference match: 44 unique top-side placements.
- Manual assembly list: `OLED1` only, one per board.
