# Hack The Badge / Hacking Box V2 Phase 1 Hardware Specification

Status: Phase 1 project description and hardware requirements draft. This
document is prepared for JLCPCB fabrication and PCBA support review. It is not a
schematic, PCB layout, Gerber package, BOM/CPL release, or production approval.

## Project Overview

Hack The Badge is a hardware hacking badge project for the Aegis booth at the
MSG CTF event. The board should look and feel like an event badge while also
serving as a small interactive challenge device. Participants connect to and
interact with the badge through USB Serial, UART, exposed challenge pads,
buttons, LEDs, and a small OLED display.

The goal of Hacking Box V2 Phase 1 is to define a manufacturable PCB baseline
that can replace or extend the existing V1 prototype while preserving the
participant-facing challenge flow as much as possible. This phase documents the
requirements and open questions that must be approved before schematic capture
and PCB layout begin.

## Why JLCPCB Support Is Needed

The project is moving from a prototype-style build toward a repeatable
small-run PCB suitable for event use. We are preparing to request support from
JLCPCB for:

- Reviewing the proposed hardware architecture before schematic capture.
- Selecting parts suitable for low-volume JLCPCB SMT assembly.
- Checking whether the participant-accessible interfaces are electrically safe.
- Reducing manual wiring and assembly errors compared with the V1 prototype.
- Confirming whether the planned OLED, USB-C, buttons, LEDs, and buzzer are
  practical for PCBA or should be handled as manual assembly.
- Preparing a clear requirements package before generating Gerbers, BOM, and
  CPL files.

Phase 1 does not create a schematic, PCB layout, Gerber ZIP, BOM, or CPL. These
documents are intended to align the project scope and approval items before the
next hardware design phase.

## Target Use Case

| Item | Requirement |
| --- | --- |
| Event role | CTF booth hardware hacking badge / Hacking Box |
| Users | Participants, booth staff, firmware maintainers |
| Expected quantity | Small run, assumed 5-10 units unless approved otherwise |
| Power | USB-powered by default |
| Participant interfaces | USB Serial, 3.3 V UART, intentional GPIO challenge pads |
| Staff interfaces | USB recovery/flashing, optional Wi-Fi/BLE management |
| Visual identity | Aegis / MSG CTF branding, OLED status, PCB silkscreen |
| Manufacturing target | 2-layer PCB, mostly single-side SMT assembly where practical |

## Recommended Hardware Architecture

| Function | Phase 1 baseline | Reason |
| --- | --- | --- |
| MCU | ESP32-S3-WROOM module | Native USB, optional Wi-Fi/BLE, enough memory, lower RF layout risk than a bare chip |
| Logic voltage | 3.3 V | Matches ESP32-S3 and modern OLED modules |
| USB | USB-C device port | Power, serial console, firmware upload, staff recovery |
| Display | 0.96 inch 128x64 I2C OLED | Compact logo, status, and challenge text display |
| Input | Three tactile switches | Left/OK/right controls, mini-game input, or admin-unlock gesture |
| Output | Five status LEDs | Clear challenge progress and solved-state indication |
| Audio | Passive buzzer with MOSFET driver, if approved | Audible feedback without directly loading an MCU GPIO |
| Challenge I/O | UART plus three protected GPIO pads | Intentional hardware hacking surface |
| Wireless | Staff-only Wi-Fi/BLE, if used | Reset, provisioning, and status monitoring without exposing management functions to players |

## Electrical Requirements

### USB And Power

- USB-C should be configured as a USB 2.0 device port.
- VBUS should feed a 3.3 V regulator with enough current and thermal margin for
  the ESP32-S3, OLED, LEDs, and optional buzzer.
- USB D+ and D- should include ESD protection and follow ESP32-S3 native USB
  routing recommendations.
- Staff recovery access for EN/reset and BOOT mode must be available.
- Battery charging is out of scope unless separately approved.

### Controller

- Prefer an ESP32-S3-WROOM module variant that is available through the selected
  assembly flow.
- Respect the ESP32-S3 module antenna keep-out area.
- Avoid using boot strapping pins for participant-facing challenge signals.
- Select a module with enough firmware headroom for the OLED UI, challenge
  logic, and optional staff management features.

### Display

- Use an SSD1306/SSD1315-compatible 128x64 I2C OLED.
- Treat the default I2C address as `0x3C` until the exact module datasheet is
  confirmed.
- If the OLED module is not suitable or economical for JLCPCB assembly, it may
  be hand-soldered after PCBA.
- Firmware should be able to show the Aegis / MSG CTF logo and challenge status
  on the display.

### Participant-Accessible Interfaces

- USB Serial remains the primary participant interface.
- Provide a separate 3.3 V UART TX/RX interface through labeled pads or a small
  header.
- Add series resistors or equivalent protection to exposed challenge GPIO pads.
- All exposed digital signals must be documented as 3.3 V only and not
  5 V tolerant.
- Keep I2C internal by default unless the final challenge design explicitly
  requires exposing it.

### Feedback Devices

- Status LEDs should be active-high unless V1 firmware review requires a
  different polarity.
- Buttons should be active-low with firmware pull-ups or hardware pull-ups.
- If a passive buzzer is used, it must be driven with PWM rather than a static
  high level.
- The buzzer should be driven through a MOSFET or transistor driver instead of
  directly from an MCU GPIO.

## V1 Firmware Compatibility Review

This repository does not currently include V1 firmware source files such as
Arduino `.ino`, C/C++ source, PlatformIO configuration, or a documented V1 pin
map. Therefore, Phase 1 cannot claim binary compatibility or source-level
compatibility with V1.

The inferred compatibility requirements are:

- Preserve the participant-facing USB Serial challenge workflow.
- If V1 used a UART challenge, port that behavior to a 3.3 V UART interface.
- Preserve visible challenge progress through multiple status LEDs.
- If V1 used physical button input, preserve the same participant-facing
  interaction using ESP32-S3 GPIO inputs.
- If V1 used a display, port the logo/status behavior to a 128x64 I2C OLED.
- Staff must be able to recover boards at the event using USB flashing, reset,
  and BOOT mode access.
- Because ESP32-S3 cannot run ATmega328P/Arduino Nano binaries, V2 firmware
  should be treated as a port or rewrite.

Before schematic capture, the actual V1 firmware repository or source archive
should be reviewed for:

- V1 pin assignments.
- Serial baud rate and command protocol.
- Startup, reset, and challenge state behavior.
- Timing-sensitive GPIO behavior.
- Display library and resolution assumptions.
- Any dependency on Arduino Nano 5 V electrical behavior.

## Mechanical And Visual Requirements

- Use a badge-like PCB outline, preferably inspired by the Aegis shield.
- Preferred visual direction: black solder mask with white silkscreen.
- The front side should clearly show the Hack The Badge, Aegis, and MSG CTF
  identity.
- USB-C should be placed on an accessible board edge with cable clearance.
- Participant pads should be reachable and identifiable, but the labeling
  should not reveal the complete challenge solution.
- Staff-only recovery pads should be separated from the primary participant
  interaction area.

## JLCPCB Review Questions

- Which ESP32-S3-WROOM module variant is recommended for availability and PCBA
  cost?
- Should the OLED module be included in PCBA or handled as manual assembly?
- Are the proposed USB-C receptacle, tactile switches, LEDs, and buzzer suitable
  for single-side SMT assembly?
- Is an input fuse/PTC recommended for a participant-handled USB-powered board?
- Are additional ESD or protection components recommended for exposed UART and
  challenge pads?
- Are there any design-for-manufacturing concerns with a shield-shaped outline
  and decorative silkscreen artwork?

## Phase 1 Deliverables

- `docs/rev3/design/hardware-spec.md`: project description and hardware requirements.
- `docs/rev3/design/decisions.md`: approved decisions, deferred decisions, and open items.
- `docs/rev3/design/pin-map.md`: proposed pin map and V1 firmware compatibility notes.

## Out Of Scope For Phase 1

- KiCad schematic creation.
- PCB layout.
- Gerber, BOM, or CPL generation.
- Final component purchase.
- Production order placement.
- Firmware port implementation.
