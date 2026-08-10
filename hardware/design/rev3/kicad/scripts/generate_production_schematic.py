#!/usr/bin/env python3
"""Generate a reviewable KiCad legacy schematic from the production PCB.

KiCad opens the generated legacy schematic together with its cache library and
converts it to the current .kicad_sch format on save. The PCB remains untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
LEGACY_PATH = ROOT / "hacking_box_v2.sch"
CACHE_LIBRARY_PATH = ROOT / "hacking_box_v2-cache.lib"


@dataclass(frozen=True)
class PinDef:
    number: str
    name: str
    x: int
    y: int
    side: str


@dataclass(frozen=True)
class SymbolDef:
    name: str
    reference: str
    half_width: int
    top: int
    bottom: int
    pins: tuple[PinDef, ...]


def two_pin(name: str, reference: str, pin1: str, pin2: str) -> SymbolDef:
    return SymbolDef(
        name,
        reference,
        150,
        110,
        -110,
        (
            PinDef("1", pin1, -350, 0, "left"),
            PinDef("2", pin2, 350, 0, "right"),
        ),
    )


ESP32_PIN_NAMES = {
    "1": "GND",
    "2": "3V3",
    "3": "EN",
    "4": "IO4",
    "5": "IO5",
    "6": "IO6",
    "7": "IO7",
    "8": "IO15",
    "9": "IO16",
    "10": "IO17",
    "11": "IO18",
    "12": "IO8",
    "13": "USB_D-",
    "14": "USB_D+",
    "15": "IO3",
    "16": "IO46",
    "17": "IO9",
    "18": "IO10",
    "19": "IO11",
    "20": "IO12",
    "21": "IO13",
    "22": "IO14",
    "23": "IO21",
    "24": "IO47",
    "25": "IO48",
    "26": "IO45",
    "27": "IO0",
    "28": "IO35",
    "29": "IO36",
    "30": "IO37",
    "31": "IO38",
    "32": "IO39",
    "33": "IO40",
    "34": "IO41",
    "35": "IO42",
    "36": "RXD0",
    "37": "TXD0",
    "38": "IO2",
    "39": "IO1",
    "40": "GND",
    "41": "GND_EP",
}


def esp32_symbol() -> SymbolDef:
    pins: list[PinDef] = []
    for number in range(1, 22):
        y = 1000 - (number - 1) * 100
        pins.append(
            PinDef(
                str(number),
                ESP32_PIN_NAMES[str(number)],
                -700,
                y,
                "left",
            )
        )
    for number in range(22, 42):
        y = 950 - (number - 22) * 100
        pins.append(
            PinDef(
                str(number),
                ESP32_PIN_NAMES[str(number)],
                700,
                y,
                "right",
            )
        )
    return SymbolDef("HB_ESP32", "U", 500, 1100, -1100, tuple(pins))


def side_pins(
    name: str,
    reference: str,
    pin_specs: list[tuple[str, str]],
    left_count: int,
    half_width: int = 300,
) -> SymbolDef:
    row_count = max(left_count, len(pin_specs) - left_count)
    top = max(200, ((row_count - 1) * 100) // 2 + 100)
    pins: list[PinDef] = []
    left = pin_specs[:left_count]
    right = pin_specs[left_count:]
    pin_x = ((half_width + 200 + 49) // 50) * 50
    for index, (number, pin_name) in enumerate(left):
        y = ((len(left) - 1) * 100) // 2 - index * 100
        pins.append(PinDef(number, pin_name, -pin_x, y, "left"))
    for index, (number, pin_name) in enumerate(right):
        y = ((len(right) - 1) * 100) // 2 - index * 100
        pins.append(PinDef(number, pin_name, pin_x, y, "right"))
    return SymbolDef(name, reference, half_width, top, -top, tuple(pins))


SYMBOLS = {
    "HB_R": two_pin("HB_R", "R", "1", "2"),
    "HB_C": two_pin("HB_C", "C", "1", "2"),
    "HB_LED": two_pin("HB_LED", "D", "K", "A"),
    "HB_DIODE": two_pin("HB_DIODE", "D", "K", "A"),
    "HB_SW": two_pin("HB_SW", "SW", "IN", "GND"),
    "HB_TP": SymbolDef(
        "HB_TP",
        "TP",
        120,
        100,
        -100,
        (PinDef("1", "TEST", -350, 0, "left"),),
    ),
    "HB_CONN4": side_pins(
        "HB_CONN4",
        "J",
        [("1", "GND"), ("2", "3V3"), ("3", "TX"), ("4", "RX")],
        4,
        220,
    ),
    "HB_OLED": side_pins(
        "HB_OLED",
        "DS",
        [("1", "GND"), ("2", "VCC"), ("3", "SCL"), ("4", "SDA")],
        4,
        260,
    ),
    "HB_REG3": side_pins(
        "HB_REG3",
        "U",
        [("1", "GND"), ("3", "IN"), ("2", "OUT")],
        2,
        240,
    ),
    "HB_FET3": side_pins(
        "HB_FET3",
        "Q",
        [("1", "G"), ("2", "S"), ("3", "D")],
        1,
        220,
    ),
    "HB_BUZZER": side_pins(
        "HB_BUZZER",
        "BZ",
        [("1", "+"), ("3", "NC"), ("2", "-")],
        2,
        220,
    ),
    "HB_ESD6": side_pins(
        "HB_ESD6",
        "D",
        [
            ("1", "IO1"),
            ("2", "GND"),
            ("3", "IO2"),
            ("4", "IO2"),
            ("5", "VBUS"),
            ("6", "IO1"),
        ],
        3,
        260,
    ),
    "HB_USB": side_pins(
        "HB_USB",
        "J",
        [
            ("A1", "GND_A"),
            ("A4", "VBUS_A"),
            ("A5", "CC1"),
            ("A6", "D+_A"),
            ("A7", "D-_A"),
            ("A8", "SBU1"),
            ("A9", "VBUS_A2"),
            ("A12", "GND_A2"),
            ("SH", "SHIELD"),
            ("B1", "GND_B"),
            ("B4", "VBUS_B"),
            ("B5", "CC2"),
            ("B6", "D+_B"),
            ("B7", "D-_B"),
            ("B8", "SBU2"),
            ("B9", "VBUS_B2"),
            ("B12", "GND_B2"),
        ],
        9,
        350,
    ),
    "HB_MECH": SymbolDef("HB_MECH", "H", 180, 120, -120, ()),
    "HB_ESP32": esp32_symbol(),
}


POSITIONS = {
    "J1": (1600, 1750),
    "D1": (3500, 1700),
    "R1": (4750, 1400),
    "R2": (4750, 2050),
    "U2": (3500, 2850),
    "C1": (1300, 3250),
    "C2": (2450, 3250),
    "C3": (4700, 3250),
    "C4": (1300, 3900),
    "C5": (2450, 3900),
    "C6": (3600, 3900),
    "C7": (4750, 3900),
    "C8": (5900, 3900),
    "U1": (7900, 2500),
    "R_EN": (6400, 4300),
    "C_EN": (7900, 4300),
    "R_BOOT": (9400, 4300),
    "OLED1": (12600, 1500),
    "R_SCL": (12100, 2600),
    "R_SDA": (14000, 2600),
    "C_OLED": (13050, 3150),
    "R_LED1": (10800, 4100),
    "LED1": (13100, 4100),
    "R_LED2": (10800, 4650),
    "LED2": (13100, 4650),
    "R_LED3": (10800, 5200),
    "LED3": (13100, 5200),
    "R_LED4": (10800, 5750),
    "LED4": (13100, 5750),
    "R_LED5": (10800, 6300),
    "LED5": (13100, 6300),
    "SW_EN": (1900, 7100),
    "SW_BOOT": (4100, 7100),
    "SW_ADMIN": (6300, 7100),
    "R_CHAL0": (8350, 7150),
    "P_CHAL0": (10300, 7150),
    "R_CHAL1": (8350, 7750),
    "P_CHAL1": (10300, 7750),
    "R_CHAL2": (8350, 8350),
    "P_CHAL2": (10300, 8350),
    "R_UART_TX": (1850, 8450),
    "R_UART_RX": (1850, 9100),
    "P_UART": (4500, 8750),
    "R_BZ": (11800, 7500),
    "BZ1": (14000, 7500),
    "D_BZ": (14000, 8150),
    "Q_BZ": (14000, 8750),
    "R_BZ_PD": (11800, 8750),
    "C9": (11800, 9400),
    "TP_3V3": (6400, 9250),
    "TP_GND": (7900, 9250),
    "TP_VBUS": (9400, 9250),
    "TP_EN": (6400, 9800),
    "TP_BOOT": (7900, 9800),
    "TP_UART_TX": (9400, 9800),
    "TP_UART_RX": (6400, 10350),
    "TP_OLED_SCL": (7900, 10350),
    "TP_OLED_SDA": (9400, 10350),
    "H1": (12800, 10200),
    "H2": (14300, 10200),
}


FOOTPRINT_OVERRIDES = {
    "BZ1": "HackingBox_V2:Buzzer_SMD5020_ZK",
    "C9": "Capacitor_SMD:C_0805_2012Metric",
    "D_BZ": "Diode_SMD:D_SOD-123",
    "J1": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    "OLED1": "HackingBox_V2:OLED_HS96L03W2C03",
    "Q_BZ": "Package_TO_SOT_SMD:SOT-23",
    "R_BZ": "Resistor_SMD:R_0603_1608Metric",
    "R_BZ_PD": "Resistor_SMD:R_0603_1608Metric",
    "U1": "RF_Module:ESP32-S3-WROOM-1",
    "U2": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
}


def natural_key(value: str) -> list[object]:
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", value)
    ]


def symbol_name(reference: str) -> str:
    if reference == "U1":
        return "HB_ESP32"
    if reference == "J1":
        return "HB_USB"
    if reference == "D1":
        return "HB_ESD6"
    if reference == "U2":
        return "HB_REG3"
    if reference == "OLED1":
        return "HB_OLED"
    if reference == "BZ1":
        return "HB_BUZZER"
    if reference == "Q_BZ":
        return "HB_FET3"
    if reference == "D_BZ":
        return "HB_DIODE"
    if reference.startswith("LED"):
        return "HB_LED"
    if reference.startswith("SW_"):
        return "HB_SW"
    if reference == "P_UART":
        return "HB_CONN4"
    if reference.startswith("H"):
        return "HB_MECH"
    if reference.startswith("P_CHAL") or reference.startswith("TP_"):
        return "HB_TP"
    if reference.startswith("R"):
        return "HB_R"
    if reference.startswith("C"):
        return "HB_C"
    raise RuntimeError(f"No schematic symbol mapping for {reference}")


def footprint_id(footprint: pcbnew.FOOTPRINT) -> str:
    reference = footprint.GetReference()
    if reference in FOOTPRINT_OVERRIDES:
        return FOOTPRINT_OVERRIDES[reference]
    fpid = footprint.GetFPID()
    nickname = str(fpid.GetLibNickname())
    item = str(fpid.GetLibItemName())
    if nickname:
        return f"{nickname}:{item}"
    raise RuntimeError(f"No qualified footprint mapping for {reference}: {item}")


def unique_pad_nets(footprint: pcbnew.FOOTPRINT) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for pad in footprint.Pads():
        number = pad.GetNumber()
        if not number:
            continue
        net_name = pad.GetNetname() or None
        if number in result and result[number] != net_name:
            raise RuntimeError(
                f"{footprint.GetReference()} pad {number} has conflicting nets"
            )
        result[number] = net_name
    return result


def legacy_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def library_text() -> str:
    lines = ["EESchema-LIBRARY Version 2.4", "#encoding utf-8"]
    for symbol in SYMBOLS.values():
        lines.extend(
            [
                "#",
                f"# {symbol.name}",
                "#",
                (
                    f"DEF {symbol.name} {symbol.reference} 0 40 Y Y "
                    "1 F N"
                ),
                (
                    f'F0 "{symbol.reference}" 0 {symbol.top + 120} '
                    "50 H V C CNN"
                ),
                (
                    f'F1 "{symbol.name}" 0 {symbol.bottom - 120} '
                    "50 H V C CNN"
                ),
                "DRAW",
                (
                    f"S {-symbol.half_width} {symbol.top} "
                    f"{symbol.half_width} {symbol.bottom} 0 1 12 f"
                ),
            ]
        )
        for pin in symbol.pins:
            orientation = "R" if pin.side == "left" else "L"
            lines.append(
                (
                    f"X {pin.name} {pin.number} {pin.x} {pin.y} 200 "
                    f"{orientation} 40 40 1 1 P"
                )
            )
        lines.extend(["ENDDRAW", "ENDDEF"])
    lines.extend(["#", "#End Library", ""])
    return "\n".join(lines)


def component_text(
    reference: str,
    value: str,
    footprint: str,
    symbol: SymbolDef,
    x: int,
    y: int,
    timestamp: int,
) -> list[str]:
    field_y = y - symbol.top - 130
    return [
        "$Comp",
        f"L {symbol.name} {reference}",
        f"U 1 1 {timestamp:08X}",
        f"P {x} {y}",
        (
            f'F 0 "{legacy_escape(reference)}" H {x} {field_y} '
            "50  0000 C CNN"
        ),
        (
            f'F 1 "{legacy_escape(value)}" H {x} {field_y + 100} '
            "50  0000 C CNN"
        ),
        (
            f'F 2 "{legacy_escape(footprint)}" H {x} {y} '
            "50  0001 C CNN"
        ),
        f'F 3 "" H {x} {y} 50  0001 C CNN',
        f"\t1    {x} {y}",
        "\t1    0    0    -1",
        "$EndComp",
    ]


def pin_position(component_x: int, component_y: int, pin: PinDef) -> tuple[int, int]:
    return component_x + pin.x, component_y - pin.y


def connection_text(
    component_x: int,
    component_y: int,
    pin: PinDef,
    net_name: str | None,
) -> list[str]:
    x, y = pin_position(component_x, component_y, pin)
    if net_name is None:
        return [f"NoConn ~ {x} {y}"]
    if pin.side == "left":
        end_x = x - 200
        orientation = 0
    else:
        end_x = x + 200
        orientation = 2
    return [
        "Wire Wire Line",
        f"\t{x} {y} {end_x} {y}",
        f"Text GLabel {end_x} {y} {orientation}    40   BiDi ~ 0",
        net_name,
    ]


def note(x: int, y: int, text: str, size: int = 80) -> list[str]:
    return [f"Text Notes {x} {y} 0    {size}   ~ 16", text]


def schematic_text(board: pcbnew.BOARD) -> str:
    footprints = {
        footprint.GetReference(): footprint
        for footprint in board.GetFootprints()
    }
    if set(footprints) != set(POSITIONS):
        missing = sorted(set(footprints) - set(POSITIONS), key=natural_key)
        extra = sorted(set(POSITIONS) - set(footprints), key=natural_key)
        raise RuntimeError(f"Position map mismatch; missing={missing}, extra={extra}")

    lines = [
        "EESchema Schematic File Version 4",
        "LIBS:hacking_box_v2-cache",
        "EELAYER 29 0",
        "EELAYER END",
        "$Descr A3 16535 11693",
        "Sheet 1 1",
        'Title "Hacking Badge Ver.3 Production Circuit"',
        'Date "2026-07-28"',
        'Rev "3.1"',
        'Comp "DKU Aegis x MSG CTF"',
        'Comment1 "Reverse-captured from the routed production PCB"',
        'Comment2 "ESP32-S3, USB-C, OLED, LEDs, controls, UART and buzzer"',
        "$EndDescr",
    ]
    lines.extend(note(650, 550, "HACKING BADGE VER.3 - PRODUCTION SCHEMATIC", 110))
    lines.extend(note(650, 850, "USB-C / POWER"))
    lines.extend(note(6500, 850, "ESP32-S3 CONTROLLER"))
    lines.extend(note(11200, 850, "OLED DISPLAY"))
    lines.extend(note(10200, 3600, "STATUS LEDS"))
    lines.extend(note(650, 6550, "PLAYER CONTROLS"))
    lines.extend(note(7600, 6550, "CHALLENGE GPIO PADS"))
    lines.extend(note(650, 8000, "PLAYER UART"))
    lines.extend(note(11100, 6900, "BUZZER DRIVER"))
    lines.extend(note(5900, 8850, "REAR STAFF DEBUG PADS"))
    lines.extend(
        note(
            650,
            10800,
            "All exposed participant logic is 3.3 V. C0/C1/C2 are protected challenge GPIO pads.",
            55,
        )
    )

    for index, reference in enumerate(
        sorted(footprints, key=natural_key),
        start=1,
    ):
        footprint = footprints[reference]
        symbol = SYMBOLS[symbol_name(reference)]
        x, y = POSITIONS[reference]
        pad_nets = unique_pad_nets(footprint)
        symbol_pin_numbers = {pin.number for pin in symbol.pins}
        if set(pad_nets) != symbol_pin_numbers:
            raise RuntimeError(
                f"{reference} pin mismatch: PCB={sorted(pad_nets)} "
                f"symbol={sorted(symbol_pin_numbers)}"
            )
        lines.extend(
            component_text(
                reference,
                footprint.GetValue(),
                footprint_id(footprint),
                symbol,
                x,
                y,
                0x71000000 + index,
            )
        )
        for pin in symbol.pins:
            lines.extend(connection_text(x, y, pin, pad_nets[pin.number]))

    lines.extend(["$EndSCHEMATC", ""])
    return "\n".join(lines)


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    CACHE_LIBRARY_PATH.write_text(library_text(), encoding="utf-8")
    LEGACY_PATH.write_text(schematic_text(board), encoding="utf-8")
    print(f"Wrote {CACHE_LIBRARY_PATH}")
    print(f"Wrote {LEGACY_PATH}")


if __name__ == "__main__":
    main()
