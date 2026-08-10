# Hack The Badge / Hacking Box V2 Phase 1 Decision Log

Status: Phase 1 decision log for JLCPCB support preparation. Items marked as
"approved for Phase 1" are approved only as requirements for the next design
step. They are not final PCB fabrication approval.

## Approved For Phase 1

| ID | Decision | Reason |
| --- | --- | --- |
| D-001 | Prepare documentation before schematic and PCB work. | The project needs a clear support package before hardware design proceeds. |
| D-002 | Target a small-run event PCB for Hack The Badge / Hacking Box V2. | The device is for a CTF booth, not mass production. |
| D-003 | Use an ESP32-S3-WROOM module as the recommended MCU baseline. | It provides native USB, optional Wi-Fi/BLE, enough memory, and lower RF risk than a bare chip. |
| D-004 | Use USB-C as the default connector for power, serial, and recovery. | It is convenient for both participants and booth staff. |
| D-005 | Limit participant-facing interfaces to USB Serial, UART, and protected challenge GPIO pads. | This provides an intentional hacking surface while reducing accidental exposure of fragile signals. |
| D-006 | Design exposed digital interfaces for 3.3 V logic. | This matches ESP32-S3 and modern peripheral requirements. |
| D-007 | Include a 128x64 I2C OLED as the baseline display. | It can show logos, status, and challenge messages in a compact area. |
| D-008 | Include multiple status LEDs. | Participants and staff can quickly read challenge progress. |
| D-009 | Include three tactile switches as baseline inputs. | They can support left/OK/right navigation, mini-games, or an admin-unlock gesture. |
| D-010 | Treat Wi-Fi/BLE as staff-only unless separately approved for gameplay. | This helps prevent management features from becoming an unintended bypass. |
| D-011 | Exclude battery charging from Phase 1. | USB-only power is simpler, safer, and easier to review for the first PCB design. |
| D-012 | Prefer a 2-layer PCB and mostly single-side SMT assembly. | This keeps small-run fabrication and assembly cost manageable. |

## V1 Compatibility Decisions

| ID | Decision | Reason |
| --- | --- | --- |
| C-001 | Review V1 firmware before freezing the pin map. | The current repository does not include V1 firmware source, so exact compatibility cannot be verified yet. |
| C-002 | Plan V2 firmware as an ESP32-S3 port or rewrite. | Arduino Nano/ATmega328P binaries cannot run directly on ESP32-S3. |
| C-003 | Preserve participant-facing USB Serial behavior by default. | This is likely the main continuity point from the existing challenge flow. |
| C-004 | Preserve or port UART challenge behavior at 3.3 V. | UART is part of the intended hacking surface, but ESP32-S3 pins are not 5 V tolerant. |
| C-005 | Keep challenge state visible through LEDs and/or OLED. | Event staff and participants need quick visual state confirmation. |

## Open Decisions Requiring Approval

The following items must be resolved after V1 firmware review and before
schematic capture.

| ID | Area | Decision needed | Why it matters |
| --- | --- | --- | --- |
| O-001 | V1 firmware | Provide the actual V1 source, archive, or pin documentation. | Compatibility should be verified from code, not assumptions. |
| O-002 | MCU | Confirm the exact ESP32-S3-WROOM part number, flash size, and PSRAM size. | This affects BOM, firmware partitioning, price, and availability. |
| O-003 | Quantity | Confirm whether the first build is 5 units, 10 units, or another quantity. | Quantity affects unit price, spare strategy, and assembly choices. |
| O-004 | OLED assembly | Decide whether the OLED is included in PCBA or hand-soldered after assembly. | This affects BOM/CPL, footprint choice, manual work, and replacement strategy. |
| O-005 | Buzzer | Approve or remove the buzzer circuit. | It adds useful feedback but increases board area, BOM lines, and firmware work. |
| O-006 | Challenge pads | Finalize pad count, labels, protection, and intended solve path. | This defines the core hardware hacking experience. |
| O-007 | Button roles | Decide whether buttons are player controls, admin unlock, mini-game inputs, or a mix. | This affects labeling, placement, and firmware behavior. |
| O-008 | Wireless management | Define Wi-Fi/BLE mode, authentication, provisioning, and whether wireless remains enabled during attempts. | Management access must not become an unintended challenge bypass. |
| O-009 | Power budget | Confirm worst-case current for ESP32-S3 radio, OLED, LEDs, and buzzer. | This determines regulator choice and thermal margin. |
| O-010 | Protection | Decide whether USB fuse/PTC, extra ESD, or stronger GPIO protection is required. | The board will be handled directly by participants. |
| O-011 | Shape and artwork | Approve final outline, logo placement, silkscreen text, and event branding. | These affect manufacturability and sponsor-facing presentation. |
| O-012 | Staff recovery | Decide whether EN/BOOT are pads only or physical buttons. | This balances event recovery convenience against accidental participant access. |
| O-013 | Assembly vendor | Confirm JLCPCB as the first-run assembly vendor or select an alternative. | Part availability, PCBA process, and output formats depend on the vendor. |
| O-014 | Distribution model | Decide whether boards are reused, collected, or given to participants. | This affects durability expectations, labeling, and acceptable cost. |

## Risks To Resolve Before Schematic Capture

- V1 firmware is missing from this repository, so hardware compatibility
  requirements are not yet verified.
- ESP32-S3 uses 3.3 V logic; any V1 dependency on Arduino Nano 5 V behavior
  requires redesign, level shifting, or explicit removal.
- Participant-accessible pads need protection resistors and clear voltage
  labeling.
- Wi-Fi/BLE management requires authentication and a physical or procedural
  unlock policy.
- The exact OLED module pin order and availability must be confirmed before
  final footprint approval.
- Live JLCPCB stock, PCBA part class, and assembly cost should be rechecked
  immediately before final BOM approval.

## Phase 1 Exit Criteria

Phase 1 is complete when:

- The project owner has reviewed this decision log.
- The availability or absence of V1 firmware source has been explicitly
  acknowledged.
- The open decisions required for schematic capture have been approved.
- The proposed pin map has been accepted as a firmware-port target or revised
  based on V1 firmware evidence.
