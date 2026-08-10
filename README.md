# Hack The Badge Ver.3

MSG CTF 본선 동아리 부스 체험존에서 사용할 `Aegis x MSG CTF`
하드웨어 배지 프로젝트입니다. ESP32-S3 기반 보드에 OLED, 상태 LED,
버튼, UART, USB Serial, buzzer, challenge GPIO pads를 올려 참가자가
직접 보드를 분석하고 문제를 해결하는 형태로 설계했습니다.

## Sponsored By

<p align="center">
  <a href="https://easyeda.com/">
    <img src="assets/brand/sponsors/official-kit/easyeda/EasyEDA_Horz_Blue_Trans.png" alt="EasyEDA" height="48">
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://jlcpcb.com/">
    <img src="assets/brand/sponsors/official-kit/jlcpcb/JLCPCB-logo-Blue.svg" alt="JLCPCB" height="48">
  </a>
</p>

This project is supported by EasyEDA and JLCPCB. The sponsor logos above link to
their official websites as requested for the public GitHub project README.

## Current Production Revision

- Revision: Hack The Badge Ver.3
- MCU: ESP32-S3-WROOM-1-N8R8
- Display: HS96L03W2C03 0.96 inch I2C OLED, hand-soldered after PCBA
- User I/O: USB Serial, 3.3 V UART, 3 buttons, 5 status LEDs
- Challenge I/O: protected `C0`, `C1`, `C2` GPIO pads through 1 kOhm series resistors
- Admin/debug: rear staff test pads for recovery and bring-up
- Audio: passive buzzer with MOSFET driver
- PCB style: black solder mask, white silkscreen, Aegis shield outline

The editable KiCad project remains the source of truth for the routed
production PCB. The EasyEDA Pro package is prepared for sponsor/coupon workflow
and must be checked after import because EDA format conversion can rebuild
copper zones differently.

## Repository Layout

```text
assets/brand/                         Aegis, MSG CTF, EasyEDA, JLCPCB logos
docs/rev3/                            design, manufacturing, sponsorship docs
hardware/design/rev3/kicad/           editable KiCad schematic, PCB, libraries
hardware/design/rev3/reference/       BOM notes, datasheets, electrical notes
hardware/releases/rev3/jlcpcb/upload/ JLCPCB upload-ready Gerber, BOM, CPL
hardware/releases/rev3/easyeda-pro/   EasyEDA Pro import package and checklist
hardware/releases/rev3/jlcpcb/        fabrication, assembly, previews, reports
archive/                              superseded design/manufacturing history
tools/                                document generation helpers
```

## Manufacturing Outputs

JLCPCB upload files:

| Step | File |
| --- | --- |
| PCB fabrication | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_gerbers.zip` |
| PCBA BOM | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_bom.csv` |
| PCBA CPL | `hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_cpl.csv` |

EasyEDA Pro import package:

| Purpose | File |
| --- | --- |
| Import current KiCad source into EasyEDA Pro | `hardware/releases/rev3/easyeda-pro/upload/hacking_badge_v3_easyeda_pro_kicad_import.zip` |
| Previous EasyEDA Pro project archive reference | `hardware/releases/rev3/easyeda-pro/reference/ProPrj_hack_the_badge_rev.3.epro2` |

Use the JLCPCB release package for actual fabrication unless the EasyEDA Pro
conversion has been visually and electrically revalidated.

## Verification

Current checked state:

- Schematic ERC: 0 errors, 0 warnings
- Schematic-to-PCB validation: PASS
- JLCPCB manufacturing validation: PASS
- Gerber ZIP SHA256:
  `b55b42de45568e995e8cb47bb18cfc09abd5469c50e1fb60852d323a703e96b1`

Useful checks:

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc \
  --format report \
  -o hardware/design/rev3/kicad/reports/erc-final.rpt \
  hardware/design/rev3/kicad/hacking_box_v2.kicad_sch

/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 \
  hardware/design/rev3/kicad/scripts/validate_schematic_against_pcb.py

/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 \
  hardware/design/rev3/kicad/scripts/validate_manufacturing.py
```

## Notes

- KiCad filenames still use `hacking_box_v2` because early project/library names
  were preserved. The production revision is Ver.3.
- `OLED1` is excluded from the JLCPCB BOM/CPL and installed manually.
- In the JLCPCB SMT viewer, cancel automatic placement alignment reminders.
  The custom shield outline can trigger false offset warnings.
- Challenge pads are 3.3 V GPIO only. Do not expose participants to `VBUS`,
  `3V3`, `EN`, or `BOOT` shorts as puzzle mechanics unless the circuit is
  intentionally revised for that use.
