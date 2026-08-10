# JLCPCB Selected Parts

Status: Revision 3 production BOM baseline. Recheck stock in the live quote.

| Function | Selected part | LCSC part | Assembly |
| --- | --- | --- | --- |
| MCU/radio | ESP32-S3-WROOM-1-N8R8 | C2913201 | JLCPCB SMT |
| USB-C | TYPE-C-31-M-12 | C165948 | JLCPCB SMT |
| USB ESD | USBLC6-2SC6 | C2827654 | JLCPCB SMT |
| 3.3 V regulator | AMS1117-3.3 | C6186 | JLCPCB SMT |
| Passive buzzer | SMD5020-ZK | C49246955 | JLCPCB SMT |
| Buzzer MOSFET | AO3400A | C20917 | JLCPCB SMT |
| Flyback diode | 1N4148W | C917030 | JLCPCB SMT |
| Status LED | KT-0603R red | C2286 | JLCPCB SMT |
| Tactile switch | TS-1088-AR02016 | C720477 | JLCPCB SMT |
| 5.1 kohm 0603 | 0603WAF5101T5E | C23186 | JLCPCB SMT |
| 10 kohm 0603 | 0603WAF1002T5E | C25804 | JLCPCB SMT |
| 1 kohm 0603 | 0603WAF1001T5E | C21190 | JLCPCB SMT |
| 10 uF 0805 | CL21A106KAYNNNE | C15850 | JLCPCB SMT |
| 100 nF 0603 | CC0603KRX7R9BB104 | C14663 | JLCPCB SMT |
| 1 uF 0603 | CL10A105KB8NNNC | C15849 | JLCPCB SMT |

The production upload BOM is
`hardware/releases/rev3/jlcpcb/upload/hacking_badge_v3_jlcpcb_bom.csv`.

## Manual Assembly

| Function | Selected part | Source | Assembly |
| --- | --- | --- | --- |
| OLED | HS96L03W2C03, 0.96 inch white SSD1315 I2C | DeviceMart item 15963242 | Hand solder after PCBA |

Order five modules for five boards; six are recommended to keep one spare.
Use a straight 1x4 2.54 mm male header if the module is supplied without one.
Install from the front with pin order `GND, VCC, SCL, SDA`; VCC is 3.3 V only.

## Button Use

`SW_EN`, `SW_BOOT`, and `SW_ADMIN` are populated as the `<-`, `OK`, and `->`
game controls. Their legacy reference names are retained only to avoid
unnecessary CPL/reference churn.

## Intentionally Not Populated

- Dedicated reset and boot push buttons; use the rear EN/BOOT test pads.
- USB input PTC/fuse.
The buzzer and its driver are populated, not DNP.
