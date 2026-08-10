# Hack The Badge / Hacking Box V2 Phase 1 Pin Map

Status: Proposed firmware-facing pin map for review. This is not a frozen PCB
pinout. It must be checked against the V1 firmware before schematic capture.

## Pin Map Goals

- Keep USB Serial available for participants and firmware flashing.
- Provide UART and challenge GPIO pads as intentional hacking interfaces.
- Avoid ESP32-S3 boot strapping pins for normal participant challenge signals.
- Keep OLED, LEDs, buttons, and buzzer simple to port in firmware.
- Leave EN and BOOT access available for staff recovery.

## Proposed ESP32-S3 Assignment

| Function | Proposed ESP32-S3 signal | Direction | Electrical behavior | Notes |
| --- | --- | --- | --- | --- |
| USB D- | `GPIO19` | USB | Native USB | Effectively fixed for ESP32-S3 native USB |
| USB D+ | `GPIO20` | USB | Native USB | Effectively fixed for ESP32-S3 native USB |
| OLED SDA | `GPIO4` | I/O | 3.3 V I2C with pull-up | Confirm final OLED module pull-ups |
| OLED SCL | `GPIO5` | Output | 3.3 V I2C with pull-up | Assumed display address: `0x3C` |
| Challenge pad 0 | `GPIO6` | I/O | 3.3 V through series resistor | Expose only after challenge design approval |
| Challenge pad 1 | `GPIO7` | I/O | 3.3 V through series resistor | Expose only after challenge design approval |
| Challenge pad 2 | `GPIO8` | I/O | 3.3 V through series resistor | Expose only after challenge design approval |
| Left button | `GPIO9` | Input | Active-low with pull-up | Player control or menu navigation |
| OK button | `GPIO10` | Input | Active-low with pull-up | Confirm/action input |
| Right button | `GPIO12` | Input | Active-low with pull-up | Player control or admin-chord candidate |
| Status LED 1 | `GPIO13` | Output | Active-high | Initialize low at boot |
| Status LED 2 | `GPIO14` | Output | Active-high | Initialize low at boot |
| Status LED 3 | `GPIO15` | Output | Active-high | Initialize low at boot |
| Status LED 4 | `GPIO16` | Output | Active-high | Initialize low at boot |
| Status LED 5 | `GPIO17` | Output | Active-high | Initialize low at boot |
| Buzzer PWM | `GPIO18` | Output | MOSFET-driven PWM | Use only if buzzer is approved |
| Player UART TX | `GPIO43` | Output | 3.3 V through series resistor | Board transmits to participant equipment |
| Player UART RX | `GPIO44` | Input | 3.3 V through series resistor | Not 5 V tolerant |
| Boot mode | `GPIO0` | Input | Pull-up, staff access | Do not use as challenge GPIO |
| Reset / enable | `EN` | Input | Pull-up, staff access | Recovery/reset only |

## Participant-Facing Interfaces

| Interface | Signals | Voltage | Compatibility requirement |
| --- | --- | --- | --- |
| USB Serial | USB D+, USB D-, VBUS, GND | USB 5 V power, native USB data | Preserve the same user experience if V1 used a Serial command flow |
| UART pads | TX, RX, GND, optional 3V3 reference | 3.3 V logic | Port V1 UART challenge behavior to ESP32-S3 |
| Challenge pads | `GPIO6`, `GPIO7`, `GPIO8`, GND reference | 3.3 V GPIO | Final behavior must match the approved challenge design |
| Buttons | Left, OK, Right | Active-low 3.3 V | Preserve V1 physical interactions if present |

## Internal Interfaces

| Interface | Signals | Notes |
| --- | --- | --- |
| OLED | SDA, SCL, 3V3, GND | SSD1306/SSD1315-compatible 128x64 I2C OLED |
| Status LEDs | LED1-LED5 | Active-high recommended for simpler firmware logic |
| Buzzer | PWM output to driver | Passive buzzer requires PWM, not a static output |
| Wi-Fi/BLE | ESP32-S3 radio | Staff-only unless separately approved |

## Staff Recovery Interfaces

| Interface | Signals | Placement requirement |
| --- | --- | --- |
| USB flashing | USB-C | Accessible board edge with cable clearance |
| Boot mode | `GPIO0`, GND | Pad or button away from easy participant access |
| Reset | `EN`, GND | Staff-accessible pad or button |
| Debug bring-up | 3V3, GND, UART TX/RX | Useful for firmware porting and event repair |

## V1 Firmware Compatibility Notes

This repository does not currently include V1 firmware source. Once the V1
source or pin documentation is provided, review:

- Whether V1 assumes an Arduino Nano / ATmega328P pin map.
- Whether V1 depends on 5 V GPIO, analog input, EEPROM, timers, or interrupt
  pins.
- Whether V1 Serial behavior depends on USB CDC, UART baud rate, or both.
- Whether LEDs are active-high or active-low.
- Whether buttons require hardware pull-ups, pull-downs, or specific debounce
  timing.
- Whether any challenge depends on timing that may change on ESP32-S3.
- Whether display code assumes SSD1306, SSD1315, address `0x3C`, or a specific
  OLED module.

Because ESP32-S3 cannot run ATmega328P binaries, compatibility means preserving
the participant-visible behavior and challenge flow through a firmware port, not
reusing the old binary.

## Firmware Bring-Up Checklist

- Confirm USB CDC Serial connection.
- Initialize all LED pins low before showing state.
- Configure button pull-ups and debounce.
- Initialize I2C and scan for the OLED address.
- Confirm UART TX/RX orientation from the participant's perspective.
- Keep challenge GPIOs in a safe input state until firmware intentionally uses
  them.
- Keep the buzzer pin low until PWM is intentionally started.
- Confirm EN/BOOT recovery before event deployment.
