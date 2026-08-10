# Hacking Badge Ver.3 Production Schematic

Status: Connected KiCad schematic reverse-captured from the routed production
PCB on 2026-07-28.

The editable schematic is
`hardware/design/rev3/kicad/hacking_box_v2.kicad_sch`. A printable A3 PDF is
available under `hardware/design/rev3/kicad/exports/` as
`hacking_box_v2_schematic.pdf`. The schematic contains
all 60 PCB references, all 37 named nets, and every intentional no-connect.

The routed and DRC-clean `hacking_box_v2.kicad_pcb` remains the manufacturing
source of truth for this revision. The schematic and PCB are checked by the
repository validator, but they were not created through KiCad's normal
schematic-first symbol-to-footprint association flow. Review associations
before using **Update PCB from Schematic**.

## USB And Power

| Ref | Part | Connection |
| --- | --- | --- |
| `J1` | TYPE-C-31-M-12, `C165948` | USB-C VBUS, GND, D+, D-, CC1, CC2 |
| `R1`, `R2` | 5.1 kohm, `C23186` | CC1/CC2 pulldown to GND |
| `D1` | USBLC6-2SC6, `C2827654` | ESD protection for D+ and D- |
| `U2` | AMS1117-3.3, `C6186` | VBUS to regulated 3V3 |
| `C1`, `C3`, `C4`, `C5`, `C7` | 10 uF, `C15850` | USB, regulator, and module bulk capacitance |
| `C2`, `C6`, `C8` | 100 nF, `C14663` | High-frequency decoupling |

USB data connects to the ESP32-S3 native USB pins:

- `USB_D_N` -> `GPIO19`
- `USB_D_P` -> `GPIO20`

The board is USB-powered. Battery charging and a battery power path are not
included.

## Controller

| Ref | Part | Notes |
| --- | --- | --- |
| `U1` | ESP32-S3-WROOM-1-N8R8, `C2913201` | Native USB, Wi-Fi/BLE, 8 MB flash and 8 MB PSRAM variant |
| `R_EN` | 10 kohm | EN pull-up |
| `C_EN` | 1 uF | EN reset timing |
| `R_BOOT` | 10 kohm | GPIO0 pull-up |

The ESP32-S3 module antenna faces the board edge. Its antenna keep-out excludes
copper, vias, and components.

## OLED

`OLED1` is the locally sourced `HS96L03W2C03`, a white 0.96 inch 128x64 I2C
module with an SSD1315 controller. It is excluded from the JLCPCB BOM/CPL and
hand-soldered after PCBA. The footprint follows the manufacturer datasheet and
uses 2.0 mm pads with a 1.1 mm nominal PTH drill for the four-pin header. The
default address is `0x3C`.

| Signal | ESP32-S3 pin | Supporting parts |
| --- | --- | --- |
| `OLED_SDA` | `GPIO4` | 10 kohm pull-up `R_SDA` |
| `OLED_SCL` | `GPIO5` | 10 kohm pull-up `R_SCL` |
| `3V3` | Power | Local 100 nF `C_OLED` |
| `GND` | Ground | Common ground plane |

## Status LEDs

All five indicators use `KT-0603R` red LEDs (`C2286`) and 1 kohm series
resistors (`C21190`). They are active high.

| LED | GPIO | MCU-side net | LED anode net |
| --- | --- | --- | --- |
| `LED1` | `GPIO13` | `STATUS_LED_1_MCU` | `STATUS_LED_1_A` |
| `LED2` | `GPIO14` | `STATUS_LED_2_MCU` | `STATUS_LED_2_A` |
| `LED3` | `GPIO15` | `STATUS_LED_3_MCU` | `STATUS_LED_3_A` |
| `LED4` | `GPIO16` | `STATUS_LED_4_MCU` | `STATUS_LED_4_A` |
| `LED5` | `GPIO17` | `STATUS_LED_5_MCU` | `STATUS_LED_5_A` |

Each path is `GPIO -> R_LEDn -> LEDn anode`; every LED cathode returns to GND.

## Buttons

| Ref | Signal | ESP32-S3 pin | Behavior |
| --- | --- | --- | --- |
| `SW_EN` | `GAME_LEFT` / `<-` | `GPIO9` | Active low, firmware pull-up |
| `SW_BOOT` | `GAME_OK` / `OK` | `GPIO10` | Active low, firmware pull-up |
| `SW_ADMIN` | `GAME_RIGHT` / `->` | `GPIO12` | Active low, firmware pull-up |

EN and GPIO0 are available on rear staff test pads for reset and boot recovery.
The three front buttons are normal GPIO inputs for post-solve mini-games.

## Buzzer Driver

The buzzer circuit is populated in the production BOM.

| Ref | Part | Connection |
| --- | --- | --- |
| `BZ1` | SMD5020-ZK, `C49246955` | Positive to 3V3, negative to `BUZZER_SW` |
| `Q_BZ` | AO3400A, `C20917` | N-channel low-side switch |
| `R_BZ` | 1 kohm | `BUZZER_GPIO` to `BUZZER_GATE` |
| `R_BZ_PD` | 10 kohm | Gate pulldown to GND |
| `D_BZ` | 1N4148W, `C917030` | Flyback clamp from `BUZZER_SW` to 3V3 |
| `C9` | 10 uF | Local 3V3 buzzer bulk capacitor |

`GPIO18` drives `BUZZER_GPIO`. Firmware should initialize it low, then use PWM
near the buzzer's nominal resonant frequency for tones.

## Player UART And Challenge Pads

| External net | ESP32-S3 pin | Protection |
| --- | --- | --- |
| `PLAYER_UART_TX` | `GPIO43` | 1 kohm `R_UART_TX` |
| `PLAYER_UART_RX` | `GPIO44` | 1 kohm `R_UART_RX` |
| `CHAL_0` | `GPIO6` | 1 kohm `R_CHAL0` |
| `CHAL_1` | `GPIO7` | 1 kohm `R_CHAL1` |
| `CHAL_2` | `GPIO8` | 1 kohm `R_CHAL2` |

All exposed logic is 3.3 V only.

## Verification

- KiCad schematic ERC: 0 errors, 0 warnings.
- Schematic-to-PCB validation: PASS.
- Components compared: 60.
- Named nets compared: 37.
- Connected component-pin pairs compared: 149.
- Intentional no-connect pins compared: 20.
- KiCad error-level DRC: 0 violations.
- KiCad unconnected check: 0 items.
- PCB stackup: two copper layers, 1.6 mm.
- JLCPCB BOM: 15 grouped lines.
- JLCPCB CPL: 44 unique top-side placements.
- Manual assembly list: `OLED1` only.
- Gerber package: 12 required fabrication files.

Validation artifacts:

- `hardware/design/rev3/kicad/reports/erc-final.rpt`
- `hardware/design/rev3/kicad/reports/schematic-pcb-validation.txt`
- `hardware/design/rev3/kicad/reports/hacking_box_v2_schematic.xml`

Regeneration tools:

- `hardware/design/rev3/kicad/scripts/generate_production_schematic.py`
  recreates the legacy capture and
  project-local symbol library from the PCB pad/net data.
- `hardware/design/rev3/kicad/scripts/validate_schematic_against_pcb.py`
  compares references, values,
  connected pins, net names, and intentional no-connects.
