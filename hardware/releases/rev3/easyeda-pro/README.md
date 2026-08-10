# Hacking Badge Ver.3 EasyEDA Pro Package

This directory contains the EasyEDA Pro preparation package for sponsor/coupon
workflow.

## Upload / Import Files

| Purpose | File |
| --- | --- |
| Current KiCad source import package | `upload/hacking_badge_v3_easyeda_pro_kicad_import.zip` |
| Previous EasyEDA Pro archive reference | `reference/ProPrj_hack_the_badge_rev.3.epro2` |

Use the KiCad import package first when the goal is to recreate the current
production KiCad design inside EasyEDA Pro. The `.epro2` file is kept as a
reference/native archive candidate, but it was generated before the final KiCad
release checks and must not be assumed to be identical without review.

## Import Procedure

1. Open EasyEDA Pro.
2. Use the start page import flow for KiCad files, or use the EasyEDA Pro Format
   Converter if direct import fails.
3. Select `upload/hacking_badge_v3_easyeda_pro_kicad_import.zip`.
4. After import, open both schematic and PCB.
5. Rebuild/refill copper zones only if EasyEDA Pro asks for it, then compare
   against the KiCad release previews and Gerbers.
6. Run EasyEDA Pro DRC/ERC before using any generated manufacturing output.

## Required Post-Import Checks

- Board outline remains the Aegis shield shape, approximately 84.05 x 100.05 mm.
- USB-C connector sits on the bottom edge with the intentional edge overhang.
- ESP32-S3 antenna keep-out is still clear.
- Front silkscreen includes `Aegis X MSG CTF`, `HACK THE BADGE Ver.3`,
  `Developed By @Z3r0c0k3_`, full Aegis logo, and sponsor mark.
- Rear silkscreen preserves the filled Aegis silhouette and MSG CTF negative
  mark.
- `C0`, `C1`, `C2` challenge pads route through 1 kOhm series resistors to
  ESP32-S3 GPIO6, GPIO7, GPIO8.
- OLED pin order remains `GND, VCC, SCL, SDA`.
- J1, U1, U2, D1, Q_BZ, LEDs, buzzer diode, and switches have correct rotation.
- Copper zones and clearances match the KiCad/JLCPCB manufacturing release.

## Important Warning

The routed KiCad project and the JLCPCB release package remain the production
source of truth until the EasyEDA Pro import is manually reviewed. EasyEDA Pro
can import KiCad files, but format conversion can change copper-zone results.
Do not manufacture from newly generated EasyEDA Pro Gerbers until visual review,
DRC/ERC, and pin/net checks pass.

## Checksums

See `SHA256SUMS.txt`.
