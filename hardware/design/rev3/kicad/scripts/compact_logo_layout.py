#!/usr/bin/env python3
from pathlib import Path
import math
import re
from typing import Optional

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
OLED_LIBRARY = ROOT / "hacking_box_v2.pretty"
SOURCE_SVG = (
    ROOT.parents[3]
    / "assets"
    / "brand"
    / "aegis"
    / "black-white-ring.svg"
)

BOARD_CENTER_X = 62.5
BOARD_TOP = 10.0
BOARD_WIDTH = 84.0
BOARD_HEIGHT = 100.0


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


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
    removable = {"segment", "via", "gr_text", "gr_text_box", "gr_circle", "gr_poly"}
    generated_layers = (
        '(layer "Edge.Cuts")',
        '(layer "F.SilkS")',
        '(layer "B.SilkS")',
        '(layer "Cmts.User")',
        '(layer "Dwgs.User")',
    )

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
            generated_graphic = name.startswith("gr_") and any(
                layer in block_text for layer in generated_layers
            )
            if name in removable or generated_graphic:
                continue
            output.extend(block)
            continue
        output.append(line)
        index += 1

    path.write_text("".join(output), encoding="utf-8")


NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def sample_svg_path(path_data: str, curve_steps: int = 10) -> list[tuple[float, float]]:
    tokens = re.findall(rf"[A-Za-z]|{NUMBER}", path_data)
    points: list[tuple[float, float]] = []
    cursor = (0.0, 0.0)
    start = (0.0, 0.0)
    last_control: tuple[float, float] | None = None
    previous_command = ""
    command = ""
    index = 0

    def read_number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    def absolute(x: float, y: float, relative: bool) -> tuple[float, float]:
        if relative:
            return cursor[0] + x, cursor[1] + y
        return x, y

    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        if not command:
            raise ValueError("SVG path data starts without a command")

        relative = command.islower()
        operation = command.lower()

        if operation == "z":
            if not points or points[-1] != start:
                points.append(start)
            cursor = start
            last_control = None
            previous_command = operation
            command = ""
            continue

        if operation == "m":
            x, y = read_number(), read_number()
            cursor = absolute(x, y, relative)
            start = cursor
            points.append(cursor)
            command = "l" if relative else "L"
            last_control = None
        elif operation == "l":
            x, y = read_number(), read_number()
            cursor = absolute(x, y, relative)
            points.append(cursor)
            last_control = None
        elif operation == "h":
            x = read_number()
            cursor = (cursor[0] + x, cursor[1]) if relative else (x, cursor[1])
            points.append(cursor)
            last_control = None
        elif operation == "v":
            y = read_number()
            cursor = (cursor[0], cursor[1] + y) if relative else (cursor[0], y)
            points.append(cursor)
            last_control = None
        elif operation == "c":
            first = absolute(read_number(), read_number(), relative)
            second = absolute(read_number(), read_number(), relative)
            end = absolute(read_number(), read_number(), relative)
            origin = cursor
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                u = 1.0 - t
                x = (
                    u**3 * origin[0]
                    + 3 * u**2 * t * first[0]
                    + 3 * u * t**2 * second[0]
                    + t**3 * end[0]
                )
                y = (
                    u**3 * origin[1]
                    + 3 * u**2 * t * first[1]
                    + 3 * u * t**2 * second[1]
                    + t**3 * end[1]
                )
                points.append((x, y))
            cursor = end
            last_control = second
        elif operation == "s":
            if previous_command in ("c", "s") and last_control is not None:
                first = (
                    2 * cursor[0] - last_control[0],
                    2 * cursor[1] - last_control[1],
                )
            else:
                first = cursor
            second = absolute(read_number(), read_number(), relative)
            end = absolute(read_number(), read_number(), relative)
            origin = cursor
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                u = 1.0 - t
                x = (
                    u**3 * origin[0]
                    + 3 * u**2 * t * first[0]
                    + 3 * u * t**2 * second[0]
                    + t**3 * end[0]
                )
                y = (
                    u**3 * origin[1]
                    + 3 * u**2 * t * first[1]
                    + 3 * u * t**2 * second[1]
                    + t**3 * end[1]
                )
                points.append((x, y))
            cursor = end
            last_control = second
        else:
            raise ValueError(f"Unsupported SVG path command: {command}")

        previous_command = operation

    return points


def bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [item[0] for item in points]
    ys = [item[1] for item in points]
    return min(xs), min(ys), max(xs), max(ys)


def fit_points(
    points: list[tuple[float, float]],
    center_x: float,
    top: float,
    width: float,
    height: float,
) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = bounds(points)
    scale_x = width / (max_x - min_x)
    scale_y = height / (max_y - min_y)
    left = center_x - width / 2
    return [
        (
            left + (x - min_x) * scale_x,
            top + (y - min_y) * scale_y,
        )
        for x, y in points
    ]


def fit_points_to_reference(
    points: list[tuple[float, float]],
    reference: list[tuple[float, float]],
    center_x: float,
    top: float,
    width: float,
    height: float,
) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = bounds(reference)
    scale_x = width / (max_x - min_x)
    scale_y = height / (max_y - min_y)
    left = center_x - width / 2
    return [
        (
            left + (x - min_x) * scale_x,
            top + (y - min_y) * scale_y,
        )
        for x, y in points
    ]


def load_logo_paths() -> tuple[
    list[tuple[float, float]],
    list[tuple[float, float]],
    list[list[tuple[float, float]]],
]:
    svg = SOURCE_SVG.read_text(encoding="utf-8")
    entries = re.findall(r'<path\s+d="([^"]+)"([^>]*)>', svg)
    sampled = [(sample_svg_path(path_data), attrs) for path_data, attrs in entries]

    shield_index = next(
        index
        for index, (_, attrs) in enumerate(sampled)
        if 'fill="#040000"' in attrs and 'stroke="#070102"' in attrs
    )
    shield = sampled[shield_index][0]

    white_candidates = [entry[0] for entry in sampled[shield_index + 1 :]]
    silhouette = max(
        white_candidates,
        key=lambda item: (bounds(item)[2] - bounds(item)[0])
        * (bounds(item)[3] - bounds(item)[1]),
    )
    white_paths = [
        points
        for index, (points, _) in enumerate(sampled)
        if index != shield_index
    ]
    return shield, silhouette, white_paths


def fit_points_to_svg_canvas(
    points: list[tuple[float, float]],
    center_x: float,
    center_y: float,
    size: float,
) -> list[tuple[float, float]]:
    source_size = 212.6
    scale = size / source_size
    left = center_x - size / 2
    top = center_y - size / 2
    return [(left + x * scale, top + y * scale) for x, y in points]


def circle_points(
    center_x: float,
    center_y: float,
    radius: float,
    steps: int = 96,
) -> list[tuple[float, float]]:
    return [
        (
            center_x + radius * math.cos(2 * math.pi * index / steps),
            center_y + radius * math.sin(2 * math.pi * index / steps),
        )
        for index in range(steps + 1)
    ]


def footprint_map(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    return {fp.GetReference(): fp for fp in board.GetFootprints()}


def place(fp: pcbnew.FOOTPRINT, x: float, y: float, angle: float = 0.0) -> None:
    fp.SetPosition(point(x, y))
    fp.SetOrientationDegrees(angle)


def make_text(
    board: pcbnew.BOARD,
    text: str,
    x: float,
    y: float,
    size: float,
    thickness: float,
    layer: int = pcbnew.F_SilkS,
    angle: float = 0.0,
) -> pcbnew.PCB_TEXT:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    item.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    item.SetLayer(layer)
    item.SetMirrored(layer == pcbnew.B_SilkS)
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    return item


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
    item = make_text(board, text, x, y, size, thickness, layer, angle)
    board.Add(item)


def text_polyset(
    board: pcbnew.BOARD,
    text: str,
    x: float,
    y: float,
    size: float,
    thickness: float,
    layer: int,
) -> pcbnew.SHAPE_POLY_SET:
    item = make_text(board, text, x, y, size, thickness, layer)
    poly_set = pcbnew.SHAPE_POLY_SET()
    item.TransformTextToPolySet(
        poly_set,
        0,
        mm(0.01),
        pcbnew.ERROR_INSIDE,
    )
    return poly_set


def add_segment(
    board: pcbnew.BOARD,
    start: tuple[float, float],
    end: tuple[float, float],
    layer: int,
    width: float,
) -> None:
    item = pcbnew.PCB_SHAPE(board)
    item.SetShape(pcbnew.SHAPE_T_SEGMENT)
    item.SetStart(point(*start))
    item.SetEnd(point(*end))
    item.SetWidth(mm(width))
    item.SetLayer(layer)
    board.Add(item)


def add_polyline(
    board: pcbnew.BOARD,
    points: list[tuple[float, float]],
    layer: int,
    width: float,
    skip=None,
) -> None:
    for start, end in zip(points, points[1:]):
        if skip is not None and skip(start, end):
            continue
        add_segment(board, start, end, layer, width)


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


def add_filled_polygon(
    board: pcbnew.BOARD,
    points: list[tuple[float, float]],
    layer: int,
    cutouts: Optional[list[list[tuple[float, float]]]] = None,
    cutout_shapes: Optional[list[pcbnew.SHAPE_POLY_SET]] = None,
) -> None:
    def make_poly_set(
        polygon: list[tuple[float, float]],
    ) -> pcbnew.SHAPE_POLY_SET:
        polygon_points = (
            polygon[:-1] if polygon[0] == polygon[-1] else polygon
        )
        poly_set = pcbnew.SHAPE_POLY_SET()
        outline = poly_set.NewOutline()
        for x, y in polygon_points:
            poly_set.Append(point(x, y), outline)
        return poly_set

    poly_shape = make_poly_set(points)
    for cutout in cutouts or []:
        poly_shape.BooleanSubtract(make_poly_set(cutout))
    for cutout_shape in cutout_shapes or []:
        poly_shape.BooleanSubtract(cutout_shape)

    if cutout_shapes:
        # KiCad graphic polygons store one outline per item. Fracture text
        # holes into bridged outlines and preserve letter counters as separate
        # white silk islands.
        poly_shape.Fracture(True)
        for outline_index in range(poly_shape.OutlineCount()):
            outline = poly_shape.COutline(outline_index)
            outline_shape = pcbnew.SHAPE_POLY_SET()
            new_outline = outline_shape.NewOutline()
            for point_index in range(outline.PointCount()):
                outline_shape.Append(outline.CPoint(point_index), new_outline)

            item = pcbnew.PCB_SHAPE(board)
            item.SetShape(pcbnew.SHAPE_T_POLY)
            item.SetPolyShape(outline_shape)
            item.SetFilled(True)
            item.SetFillMode(pcbnew.FILL_T_FILLED_SHAPE)
            item.SetWidth(0)
            item.SetLayer(layer)
            board.Add(item)
        return

    item = pcbnew.PCB_SHAPE(board)
    item.SetShape(pcbnew.SHAPE_T_POLY)
    item.SetPolyShape(poly_shape)
    item.SetFilled(True)
    item.SetFillMode(pcbnew.FILL_T_FILLED_SHAPE)
    item.SetWidth(0)
    item.SetLayer(layer)
    board.Add(item)


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


strip_generated_board_items(BOARD_PATH)
board = pcbnew.LoadBoard(str(BOARD_PATH))
parts = footprint_map(board)

old_oled = parts["OLED1"]
if str(old_oled.GetFPID().GetLibItemName()) != "OLED_HS96L03W2C03":
    board.Remove(old_oled)
    oled = pcbnew.FootprintLoad(str(OLED_LIBRARY), "OLED_HS96L03W2C03")
    if oled is None:
        raise RuntimeError("Could not load the HS96L03W2C03 OLED footprint")
    oled.SetReference("OLED1")
    oled.SetValue("HS96L03W2C03")
    board.Add(oled)
    parts = footprint_map(board)

layout = {
    "OLED1": (62.5, 39.0, 0),
    "H1": (33.5, 24.0, 0),
    "H2": (91.5, 24.0, 0),
    "P_UART": (34.0, 31.5, 90),
    "R_UART_TX": (46.0, 29.5, 90),
    "R_UART_RX": (46.0, 33.0, 90),
    "C_OLED": (44.0, 38.0, 90),
    "R_SCL": (44.0, 42.0, 90),
    "R_SDA": (44.0, 46.0, 90),
    "LED1": (52.0, 58.0, 0),
    "LED2": (57.25, 58.0, 0),
    "LED3": (62.5, 58.0, 0),
    "LED4": (67.75, 58.0, 0),
    "LED5": (73.0, 58.0, 0),
    "R_LED1": (52.0, 61.5, 0),
    "R_LED2": (57.25, 61.5, 0),
    "R_LED3": (62.5, 61.5, 0),
    "R_LED4": (67.75, 61.5, 0),
    "R_LED5": (71.5, 61.5, 0),
    "U1": (87.5, 71.0, 270),
    "C7": (83.0, 59.0, 90),
    "C8": (86.0, 59.0, 90),
    "R_EN": (89.0, 55.5, 90),
    "C_EN": (89.0, 59.0, 90),
    "R_BOOT": (76.5, 82.5, 90),
    "U2": (33.5, 56.5, 90),
    "C1": (28.5, 53.0, 90),
    "C2": (28.5, 56.5, 90),
    "C3": (28.5, 60.0, 90),
    "C4": (33.5, 62.0, 90),
    "C5": (38.5, 55.0, 90),
    "C6": (38.5, 59.0, 90),
    "R_CHAL0": (30.0, 76.5, 90),
    "R_CHAL1": (36.0, 76.5, 90),
    "R_CHAL2": (42.0, 76.5, 90),
    "P_CHAL0": (30.0, 80.5, 0),
    "P_CHAL1": (36.0, 80.5, 0),
    "P_CHAL2": (42.0, 80.5, 0),
    "SW_EN": (52.5, 87.5, 0),
    "SW_BOOT": (62.5, 87.5, 0),
    "SW_ADMIN": (72.5, 87.5, 0),
    "D1": (62.5, 95.0, 0),
    "R1": (54.5, 96.5, 0),
    "R2": (70.5, 96.5, 0),
    "J1": (62.5, 104.5, 0),
}

for reference, (x, y, angle) in layout.items():
    if reference not in parts:
        raise RuntimeError(f"Missing footprint: {reference}")
    place(parts[reference], x, y, angle)

testpoint_layout = {
    "TP_3V3": (28.0, 57.0),
    "TP_GND": (34.0, 57.0),
    "TP_VBUS": (40.0, 57.0),
    "TP_EN": (28.0, 64.0),
    "TP_BOOT": (34.0, 64.0),
    "TP_UART_TX": (40.0, 64.0),
    "TP_UART_RX": (28.0, 71.0),
    "TP_OLED_SCL": (34.0, 71.0),
    "TP_OLED_SDA": (40.0, 71.0),
}

for reference, (x, y) in testpoint_layout.items():
    fp = parts[reference]
    if not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), False)
    place(fp, x, y, 0)

shield_source, silhouette_source, white_logo_paths = load_logo_paths()
outer = fit_points(
    shield_source,
    BOARD_CENTER_X,
    BOARD_TOP,
    BOARD_WIDTH,
    BOARD_HEIGHT,
)
inner = fit_points(
    shield_source,
    BOARD_CENTER_X,
    BOARD_TOP + 4.0,
    BOARD_WIDTH - 8.0,
    BOARD_HEIGHT - 8.0,
)

add_polyline(board, outer, pcbnew.Edge_Cuts, 0.05)


def skip_inner_border(
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    xs = (start[0], end[0])
    ys = (start[1], end[1])
    title_gap = max(ys) < 26.0 and max(xs) >= 45.0 and min(xs) <= 80.0
    module_gap = max(xs) > 82.0 and max(ys) > 57.0 and min(ys) < 84.0
    usb_gap = min(ys) > 98.0 and max(xs) >= 53.0 and min(xs) <= 72.0
    return title_gap or module_gap or usb_gap


add_polyline(board, inner, pcbnew.F_SilkS, 0.22, skip_inner_border)

add_text(board, "Aegis X MSG CTF", 62.5, 17.4, 1.30, 0.19)
add_text(board, "HACK THE BADGE Ver.3", 62.5, 20.5, 1.05, 0.16)
add_text(board, "Developed By @Z3r0c0k3_", 62.5, 23.2, 0.58, 0.10)
add_text(board, "UART", 34.5, 27.5, 0.72, 0.11)
add_text(board, "STATUS", 62.5, 54.7, 0.72, 0.11)
for index, x in enumerate((52.0, 57.25, 62.5, 67.75, 73.0), start=1):
    add_text(board, str(index), x, 55.9, 0.58, 0.09)

# Reproduce the complete circular source logo in one-color silkscreen. Black
# SVG regions are negative space that exposes the black PCB; every original
# white element, including the ring, AEGIS letters, figure, and laurels, is
# printed in white.
front_logo_center = (62.5, 71.5)
front_logo_size = 16.0
front_logo_scale = front_logo_size / 212.6
front_disk = circle_points(
    front_logo_center[0],
    front_logo_center[1],
    72.73 * front_logo_scale,
)
front_shield_cutout = fit_points_to_svg_canvas(
    shield_source,
    front_logo_center[0],
    front_logo_center[1],
    front_logo_size,
)
add_filled_polygon(
    board,
    front_disk,
    pcbnew.F_SilkS,
    cutouts=[front_shield_cutout],
)
add_circle(
    board,
    front_logo_center[0],
    front_logo_center[1],
    104.17 * front_logo_scale,
    max(0.20, 3.0 * front_logo_scale),
)
for white_path in white_logo_paths:
    add_filled_polygon(
        board,
        fit_points_to_svg_canvas(
            white_path,
            front_logo_center[0],
            front_logo_center[1],
            front_logo_size,
        ),
        pcbnew.F_SilkS,
    )

for label, x in (("C0", 30.0), ("C1", 36.0), ("C2", 42.0)):
    add_text(board, label, x, 83.0, 0.58, 0.09)
for label, x in (("<-", 52.5), ("OK", 62.5), ("->", 72.5)):
    add_text(board, label, x, 84.5, 0.80, 0.12)
add_text(board, "USB-C", 62.5, 91.8, 0.72, 0.11)

silhouette = fit_points_to_reference(
    silhouette_source,
    shield_source,
    BOARD_CENTER_X,
    BOARD_TOP,
    BOARD_WIDTH,
    BOARD_HEIGHT,
)
add_filled_polygon(
    board,
    silhouette,
    pcbnew.B_SilkS,
    cutout_shapes=[
        text_polyset(
            board,
            "DKU",
            62.5,
            81.0,
            5.8,
            0.85,
            pcbnew.B_SilkS,
        ),
        text_polyset(
            board,
            "Aegis",
            62.5,
            90.8,
            4.8,
            0.72,
            pcbnew.B_SilkS,
        )
    ],
)

for label, x, y in (
    ("3V3", 28.0, 54.7),
    ("GND", 34.0, 54.7),
    ("5V", 40.0, 54.7),
    ("EN", 28.0, 61.7),
    ("BOOT", 34.0, 61.7),
    ("TX", 40.0, 61.7),
    ("RX", 28.0, 68.7),
    ("SCL", 34.0, 68.7),
    ("SDA", 40.0, 68.7),
):
    add_text(board, label, x, y, 0.54, 0.09, pcbnew.B_SilkS)

# Production parts and their final spacing are applied after this artwork pass.
# The production DRC is the authoritative overlap/clearance check.
pcbnew.SaveBoard(str(BOARD_PATH), board)
