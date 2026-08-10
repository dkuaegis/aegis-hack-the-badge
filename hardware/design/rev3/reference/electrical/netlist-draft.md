# Hacking Badge Ver.3 Netlist Record

Status: Human-readable summary of the final PCB nets. The KiCad PCB remains the
machine-readable source of truth.

## Power

| Net | Members |
| --- | --- |
| `VBUS` | USB-C VBUS, AMS1117 input, USB-side bulk/decoupling, VBUS test pad |
| `3V3` | AMS1117 output, ESP32-S3 supply, OLED supply, pull-ups, buzzer positive, 3V3 test pad |
| `GND` | USB shield/ground, ESP32 grounds, regulator ground, capacitor returns, switches, LEDs, UART ground, MOSFET source |

## USB

| Net | Members |
| --- | --- |
| `USB_D_N` | `J1.D-`, `D1`, `U1.GPIO19` |
| `USB_D_P` | `J1.D+`, `D1`, `U1.GPIO20` |
| `USB_CC1` | `J1.CC1`, `R1`; opposite resistor end to GND |
| `USB_CC2` | `J1.CC2`, `R2`; opposite resistor end to GND |

## Control And Display

| Net | Members |
| --- | --- |
| `EN` | `U1.EN`, `R_EN`, `C_EN`, EN test pad |
| `BOOT_GPIO0` | `U1.GPIO0`, `R_BOOT`, BOOT test pad |
| `GAME_LEFT` | `U1.GPIO9`, `SW_EN.1`; `SW_EN.2` to GND |
| `GAME_OK` | `U1.GPIO10`, `SW_BOOT.1`; `SW_BOOT.2` to GND |
| `GAME_RIGHT` | `U1.GPIO12`, `SW_ADMIN.1`; `SW_ADMIN.2` to GND |
| `OLED_SDA` | `U1.GPIO4`, OLED SDA, `R_SDA` |
| `OLED_SCL` | `U1.GPIO5`, OLED SCL, `R_SCL` |

## Status LEDs

| MCU net | GPIO | Series path |
| --- | --- | --- |
| `STATUS_LED_1_MCU` | `GPIO13` | `R_LED1` -> `STATUS_LED_1_A` -> `LED1` -> GND |
| `STATUS_LED_2_MCU` | `GPIO14` | `R_LED2` -> `STATUS_LED_2_A` -> `LED2` -> GND |
| `STATUS_LED_3_MCU` | `GPIO15` | `R_LED3` -> `STATUS_LED_3_A` -> `LED3` -> GND |
| `STATUS_LED_4_MCU` | `GPIO16` | `R_LED4` -> `STATUS_LED_4_A` -> `LED4` -> GND |
| `STATUS_LED_5_MCU` | `GPIO17` | `R_LED5` -> `STATUS_LED_5_A` -> `LED5` -> GND |

## UART And Challenge

| MCU net | GPIO | Series path |
| --- | --- | --- |
| `UART_TX_MCU` | `GPIO43` | `R_UART_TX` -> `PLAYER_UART_TX` |
| `UART_RX_MCU` | `GPIO44` | `R_UART_RX` -> `PLAYER_UART_RX` |
| `CHAL_0_MCU` | `GPIO6` | `R_CHAL0` -> `CHAL_0` |
| `CHAL_1_MCU` | `GPIO7` | `R_CHAL1` -> `CHAL_1` |
| `CHAL_2_MCU` | `GPIO8` | `R_CHAL2` -> `CHAL_2` |

## Buzzer

| Net | Members |
| --- | --- |
| `BUZZER_GPIO` | `U1.GPIO18`, `R_BZ.1` |
| `BUZZER_GATE` | `R_BZ.2`, `Q_BZ.G`, `R_BZ_PD.1`; `R_BZ_PD.2` to GND |
| `BUZZER_SW` | `BZ1.-`, `Q_BZ.D`, `D_BZ.A` |
| `3V3` | `BZ1.+`, `D_BZ.K`, `C9.1`; `C9.2` to GND |
