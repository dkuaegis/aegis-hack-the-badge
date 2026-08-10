#!/usr/bin/env python3
from pathlib import Path
import re

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
OLED_LIBRARY = ROOT / "hacking_box_v2.pretty"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def footprint_map(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    return {fp.GetReference(): fp for fp in board.GetFootprints()}


def place(fp: pcbnew.FOOTPRINT, x: float, y: float, angle: float = 0.0) -> None:
    fp.SetPosition(point(x, y))
    fp.SetOrientationDegrees(angle)


def add_text(
    board: pcbnew.BOARD,
    text: str,
    x: float,
    y: float,
    size: float,
    thickness: float,
    layer: int = pcbnew.F_SilkS,
    angle: float = 0.0,
) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    item.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    item.SetLayer(layer)
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(item)


def add_circle(
    board: pcbnew.BOARD,
    x: float,
    y: float,
    radius: float,
    width: float,
    layer: int = pcbnew.F_SilkS,
) -> None:
    item = pcbnew.PCB_SHAPE(board)
    item.SetShape(pcbnew.SHAPE_T_CIRCLE)
    item.SetCenter(point(x, y))
    item.SetEnd(point(x + radius, y))
    item.SetWidth(mm(width))
    item.SetLayer(layer)
    board.Add(item)


def paren_delta(line: str) -> int:
    depth = 0
    in_string = False
    escaped = False
    for char in line:
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            depth += char == "("
            depth -= char == ")"
    return depth


def strip_generated_board_items(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    index = 0
    removable = {"segment", "via", "gr_text", "gr_text_box", "gr_circle"}

    while index < len(lines):
        line = lines[index]
        if line.startswith("\t(") and not line.startswith("\t\t"):
            name = line.strip()[1:].split(maxsplit=1)[0]
            block = [line]
            depth = paren_delta(line)
            index += 1
            while depth > 0 and index < len(lines):
                block.append(lines[index])
                depth += paren_delta(lines[index])
                index += 1
            block_text = "".join(block)
            on_work_layer = (
                '(layer "Cmts.User")' in block_text
                or '(layer "Dwgs.User")' in block_text
            )
            title_gap = False
            if name == "gr_line" and '(layer "F.SilkS")' in block_text:
                coordinates = re.findall(
                    r"\((?:start|end)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)",
                    block_text,
                )
                if len(coordinates) == 2:
                    xs = [float(item[0]) for item in coordinates]
                    ys = [float(item[1]) for item in coordinates]
                    title_gap = max(ys) < 20.0 and max(xs) >= 49.0 and min(xs) <= 76.0
            if (
                name in removable
                or (name.startswith("gr_") and on_work_layer)
                or title_gap
            ):
                continue
            output.extend(block)
            continue
        output.append(line)
        index += 1

    path.write_text("".join(output), encoding="utf-8")


strip_generated_board_items(BOARD_PATH)
board = pcbnew.LoadBoard(str(BOARD_PATH))

parts = footprint_map(board)
old_oled = parts.pop("OLED1")
board.Remove(old_oled)
oled = pcbnew.FootprintLoad(str(OLED_LIBRARY), "OLED_HS96L03W2C03")
if oled is None:
    raise RuntimeError("Could not load the HS96L03W2C03 OLED footprint")
oled.SetReference("OLED1")
oled.SetValue("HS96L03W2C03")
board.Add(oled)
parts["OLED1"] = oled

# Visual hierarchy: display and lanyard holes at the top, user indicators in
# the middle, controller and power below, service controls at the bottom.
layout = {
    "OLED1": (62.5, 38.5, 0),
    "H1": (38.5, 32.0, 0),
    "H2": (86.5, 32.0, 0),
    "J1": (20.5, 68.0, 90),
    "D1": (27.5, 68.0, 90),
    "R1": (26.0, 62.5, 90),
    "R2": (29.0, 62.5, 90),
    "U2": (35.0, 72.5, 90),
    "C1": (29.5, 73.5, 90),
    "C2": (29.5, 77.0, 90),
    "C3": (32.5, 77.0, 90),
    "C4": (38.0, 76.0, 90),
    "C5": (41.0, 73.5, 90),
    "C6": (41.0, 77.0, 90),
    "C7": (82.0, 62.5, 90),
    "C8": (84.8, 62.5, 90),
    "R_EN": (87.2, 59.5, 90),
    "C_EN": (87.2, 62.5, 90),
    "R_BOOT": (69.5, 87.0, 90),
    "R_SCL": (45.0, 52.5, 90),
    "R_SDA": (45.0, 56.0, 90),
    "C_OLED": (45.0, 49.0, 90),
    "LED1": (52.0, 58.5, 0),
    "LED2": (57.25, 58.5, 0),
    "LED3": (62.5, 58.5, 0),
    "LED4": (67.75, 58.5, 0),
    "LED5": (73.0, 58.5, 0),
    "R_LED1": (52.0, 62.0, 0),
    "R_LED2": (57.25, 62.0, 0),
    "R_LED3": (62.5, 62.0, 0),
    "R_LED4": (67.75, 62.0, 0),
    "R_LED5": (73.0, 62.0, 0),
    # At 270 degrees the module antenna and its no-copper area face right.
    "U1": (84.0, 75.0, 270),
    "P_UART": (29.0, 88.5, 90),
    "R_UART_TX": (40.0, 81.5, 90),
    "R_UART_RX": (40.0, 85.0, 90),
    "R_CHAL0": (42.0, 90.0, 90),
    "R_CHAL1": (48.0, 90.0, 90),
    "R_CHAL2": (54.0, 90.0, 90),
    "P_CHAL0": (42.0, 94.0, 0),
    "P_CHAL1": (48.0, 94.0, 0),
    "P_CHAL2": (54.0, 94.0, 0),
    "SW_EN": (58.0, 100.5, 0),
    "SW_BOOT": (67.0, 100.5, 0),
    "SW_ADMIN": (76.0, 100.5, 0),
}

for reference, (x, y, angle) in layout.items():
    place(parts[reference], x, y, angle)

# Staff-only test pads are placed on the back to keep the badge face readable.
testpoint_layout = {
    "TP_3V3": (73.0, 92.0),
    "TP_GND": (79.0, 92.0),
    "TP_VBUS": (85.0, 92.0),
    "TP_EN": (73.0, 97.5),
    "TP_BOOT": (79.0, 97.5),
    "TP_UART_TX": (85.0, 97.5),
    "TP_UART_RX": (73.0, 103.0),
    "TP_OLED_SCL": (79.0, 103.0),
    "TP_OLED_SDA": (85.0, 103.0),
}

for reference, (x, y) in testpoint_layout.items():
    fp = parts[reference]
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), False)
    place(fp, x, y, 0)

# White front silkscreen. Labels are intentionally sparse and tied to a nearby
# control or connector; no manufacturing notes are left on visible layers.
add_text(board, "Aegis x MSG CTF", 62.5, 16.5, 1.8, 0.24)
add_text(board, "HACKING BADGE V2", 62.5, 20.0, 0.9, 0.14)
add_text(board, "GND   3V3   SCL   SDA", 62.5, 54.2, 0.62, 0.10)
for index, x in enumerate((52.0, 57.25, 62.5, 67.75, 73.0), start=1):
    add_text(board, str(index), x, 55.8, 0.68, 0.11)
add_text(board, "USB-C", 24.5, 58.5, 0.72, 0.11)
add_text(board, "UART  G 3 T R", 25.0, 94.0, 0.68, 0.10)
add_text(board, "CHALLENGE", 48.0, 86.5, 0.72, 0.11)
add_text(board, "C0       C1       C2", 48.0, 97.0, 0.62, 0.10)
add_text(board, "RESET", 58.0, 96.8, 0.66, 0.10)
add_text(board, "BOOT", 67.0, 96.8, 0.66, 0.10)
add_text(board, "ADMIN", 76.0, 96.8, 0.66, 0.10)
add_circle(board, 38.5, 32.0, 3.2, 0.20)
add_circle(board, 86.5, 32.0, 3.2, 0.20)

# Back-side test-pad legend.
for label, x, y in (
    ("3V3", 73.0, 89.8),
    ("GND", 79.0, 89.8),
    ("5V", 85.0, 89.8),
    ("EN", 73.0, 95.3),
    ("BOOT", 79.0, 95.3),
    ("TX", 85.0, 95.3),
    ("RX", 73.0, 100.8),
    ("SCL", 79.0, 100.8),
    ("SDA", 85.0, 100.8),
):
    add_text(board, label, x, y, 0.58, 0.09, pcbnew.B_SilkS)


def find_courtyard_overlaps(
    board: pcbnew.BOARD,
) -> list[tuple[str, str, float]]:
    overlaps: list[tuple[str, str, float]] = []
    for flipped, layer in (
        (False, pcbnew.F_CrtYd),
        (True, pcbnew.B_CrtYd),
    ):
        courtyards = []
        for fp in board.GetFootprints():
            if fp.IsFlipped() != flipped:
                continue
            courtyard = fp.GetCourtyard(layer)
            if courtyard.OutlineCount() and not courtyard.IsEmpty():
                courtyards.append((fp.GetReference(), courtyard))
        for index, (left_ref, left) in enumerate(courtyards):
            for right_ref, right in courtyards[index + 1 :]:
                intersection = left.CloneDropTriangulation()
                intersection.BooleanIntersection(right)
                overlap_mm2 = intersection.Area() / 1_000_000_000_000
                if overlap_mm2 > 0.0001:
                    overlaps.append((left_ref, right_ref, overlap_mm2))
    return overlaps


overlaps = find_courtyard_overlaps(board)
if overlaps:
    details = ", ".join(
        f"{left}/{right} ({area:.3f} mm^2)"
        for left, right, area in overlaps
    )
    raise RuntimeError(f"Footprint courtyard overlap: {details}")

pcbnew.SaveBoard(str(BOARD_PATH), board)
