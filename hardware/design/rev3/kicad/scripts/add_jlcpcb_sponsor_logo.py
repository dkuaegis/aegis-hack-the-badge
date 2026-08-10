#!/usr/bin/env python3
"""Add the sponsor marks to the front silkscreen."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
PROJECT_ROOT = ROOT.parents[3]
KICAD_PYTHON = Path(
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)
JLCPCB_SVG = (
    ROOT.parents[3]
    / "assets"
    / "brand"
    / "sponsors"
    / "official-kit"
    / "jlcpcb"
    / "JLCPCB-logo-White.svg"
)
JLCPCB_PNG = (
    PROJECT_ROOT
    / "assets"
    / "brand"
    / "sponsors"
    / "official-kit"
    / "jlcpcb"
    / "JLCPCB-logo-white-Trans.png"
)
EASYEDA_PNG = (
    PROJECT_ROOT
    / "assets"
    / "brand"
    / "sponsors"
    / "official-kit"
    / "easyeda"
    / "EasyEDA_Horz_Blue_Trans.png"
)
GROUP_NAME = "JLCPCB_SPONSOR_LOGO"

LOGO_CENTER_X = 39.0
CAPTION_Y = 63.9
EASYEDA_TOP_Y = 64.8
EASYEDA_WIDTH = 22.0
JLCPCB_TOP_Y = 69.7
JLCPCB_WIDTH = 22.0
RASTER_PITCH_MM = 0.075

RESTORED_BORDER_SEGMENTS = (
    ((27.977794, 84.657241), (30.879856, 88.698940)),
    ((30.879856, 88.698940), (34.906992, 91.879416)),
    ((34.906992, 91.879416), (40.211408, 93.943099)),
)

NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def parse_svg_path(
    path_data: str, curve_steps: int = 16
) -> list[list[tuple[float, float]]]:
    tokens = re.findall(rf"[A-Za-z]|{NUMBER}", path_data)
    contours: list[list[tuple[float, float]]] = []
    contour: list[tuple[float, float]] = []
    cursor = (0.0, 0.0)
    start = (0.0, 0.0)
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
            if contour[-1] != start:
                contour.append(start)
            contours.append(contour)
            contour = []
            cursor = start
            command = ""
            continue

        if operation == "m":
            x, y = read_number(), read_number()
            cursor = absolute(x, y, relative)
            start = cursor
            if contour:
                contours.append(contour)
            contour = [cursor]
            command = "l" if relative else "L"
        elif operation == "l":
            x, y = read_number(), read_number()
            cursor = absolute(x, y, relative)
            contour.append(cursor)
        elif operation == "h":
            x = read_number()
            cursor = (cursor[0] + x, cursor[1]) if relative else (x, cursor[1])
            contour.append(cursor)
        elif operation == "v":
            y = read_number()
            cursor = (cursor[0], cursor[1] + y) if relative else (cursor[0], y)
            contour.append(cursor)
        elif operation == "q":
            control = absolute(read_number(), read_number(), relative)
            end = absolute(read_number(), read_number(), relative)
            origin = cursor
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                u = 1.0 - t
                contour.append(
                    (
                        u * u * origin[0]
                        + 2 * u * t * control[0]
                        + t * t * end[0],
                        u * u * origin[1]
                        + 2 * u * t * control[1]
                        + t * t * end[1],
                    )
                )
            cursor = end
        elif operation == "c":
            control1 = absolute(read_number(), read_number(), relative)
            control2 = absolute(read_number(), read_number(), relative)
            end = absolute(read_number(), read_number(), relative)
            origin = cursor
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                u = 1.0 - t
                contour.append(
                    (
                        u * u * u * origin[0]
                        + 3 * u * u * t * control1[0]
                        + 3 * u * t * t * control2[0]
                        + t * t * t * end[0],
                        u * u * u * origin[1]
                        + 3 * u * u * t * control1[1]
                        + 3 * u * t * t * control2[1]
                        + t * t * t * end[1],
                    )
                )
            cursor = end
        else:
            raise ValueError(f"Unsupported SVG path command: {command}")

    if contour:
        contours.append(contour)
    return contours


def signed_area(contour: list[tuple[float, float]]) -> float:
    return sum(
        left[0] * right[1] - right[0] * left[1]
        for left, right in zip(contour, contour[1:])
    ) / 2


def contains(
    contour: list[tuple[float, float]], target: tuple[float, float]
) -> bool:
    x, y = target
    inside = False
    for left, right in zip(contour, contour[1:]):
        x1, y1 = left
        x2, y2 = right
        crosses = (y1 > y) != (y2 > y)
        if crosses and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def transform_contours(
    contours: list[list[tuple[float, float]]],
    center_x: float,
    top_y: float,
    width: float,
) -> list[list[tuple[float, float]]]:
    all_points = [item for contour in contours for item in contour]
    min_x = min(item[0] for item in all_points)
    min_y = min(item[1] for item in all_points)
    max_x = max(item[0] for item in all_points)
    scale = width / (max_x - min_x)
    left = center_x - width / 2
    return [
        [
            (
                left + (x - min_x) * scale,
                top_y + (y - min_y) * scale,
            )
            for x, y in contour
        ]
        for contour in contours
    ]


def add_filled_contour(
    board: pcbnew.BOARD,
    group: pcbnew.PCB_GROUP,
    outline: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]],
) -> int:
    poly_set = pcbnew.SHAPE_POLY_SET()
    outline_index = poly_set.NewOutline()
    for x, y in outline[:-1]:
        poly_set.Append(point(x, y), outline_index)
    if not holes:
        item = pcbnew.PCB_SHAPE(board)
        item.SetShape(pcbnew.SHAPE_T_POLY)
        item.SetPolyShape(poly_set)
        item.SetFilled(True)
        item.SetFillMode(pcbnew.FILL_T_FILLED_SHAPE)
        item.SetWidth(0)
        item.SetLayer(pcbnew.F_SilkS)
        board.Add(item)
        group.AddItem(item)
        return 1

    for hole in holes:
        hole_index = poly_set.NewHole(outline_index)
        for x, y in hole[:-1]:
            poly_set.Append(point(x, y), outline_index, hole_index)

    # Graphic polygons store one outline per item. Fracturing bridges each
    # counter to its parent while preserving the visible SVG shape.
    poly_set.Fracture(True)
    added = 0
    for index in range(poly_set.OutlineCount()):
        source = poly_set.COutline(index)
        shape = pcbnew.SHAPE_POLY_SET()
        target = shape.NewOutline()
        for point_index in range(source.PointCount()):
            shape.Append(source.CPoint(point_index), target)

        item = pcbnew.PCB_SHAPE(board)
        item.SetShape(pcbnew.SHAPE_T_POLY)
        item.SetPolyShape(shape)
        item.SetFilled(True)
        item.SetFillMode(pcbnew.FILL_T_FILLED_SHAPE)
        item.SetWidth(0)
        item.SetLayer(pcbnew.F_SilkS)
        board.Add(item)
        group.AddItem(item)
        added += 1
    return added


def restore_border_segments(board: pcbnew.BOARD) -> int:
    def close(left: float, right: float) -> bool:
        return abs(left - right) < 0.001

    existing = set()
    for item in board.Drawings():
        if (
            isinstance(item, pcbnew.PCB_SHAPE)
            and item.GetLayer() == pcbnew.F_SilkS
            and item.GetShape() == pcbnew.SHAPE_T_SEGMENT
        ):
            start = item.GetStart()
            end = item.GetEnd()
            existing.add(
                (
                    (round(pcbnew.ToMM(start.x), 6), round(pcbnew.ToMM(start.y), 6)),
                    (round(pcbnew.ToMM(end.x), 6), round(pcbnew.ToMM(end.y), 6)),
                )
            )

    added = 0
    for start, end in RESTORED_BORDER_SEGMENTS:
        forward = (
            (round(start[0], 6), round(start[1], 6)),
            (round(end[0], 6), round(end[1], 6)),
        )
        reverse = (forward[1], forward[0])
        if forward in existing or reverse in existing:
            continue
        item = pcbnew.PCB_SHAPE(board)
        item.SetShape(pcbnew.SHAPE_T_SEGMENT)
        item.SetStart(point(*start))
        item.SetEnd(point(*end))
        item.SetWidth(mm(0.22))
        item.SetLayer(pcbnew.F_SilkS)
        board.Add(item)
        added += 1
    return added


def remove_existing_group(board: pcbnew.BOARD) -> int:
    removed = 0
    for group in list(board.Groups()):
        if group.GetName() != GROUP_NAME:
            continue
        for item in list(group.GetItems()):
            group.RemoveItem(item)
            board.Remove(item)
            removed += 1
        board.Remove(group)
    return removed


def extract_svg_paths(svg: str) -> list[str]:
    return re.findall(r"<path\b[^>]*\bd=\"([^\"]+)\"", svg, flags=re.DOTALL)


def prepare_jlcpcb_contours() -> list[list[tuple[float, float]]]:
    svg = JLCPCB_SVG.read_text(encoding="utf-8")
    paths = extract_svg_paths(svg)
    if not paths:
        raise RuntimeError(f"No SVG path found in {JLCPCB_SVG}")
    contours: list[list[tuple[float, float]]] = []
    for path_data in paths:
        contours.extend(parse_svg_path(path_data))
    return transform_contours(
        contours,
        LOGO_CENTER_X,
        JLCPCB_TOP_Y,
        JLCPCB_WIDTH,
    )


def prepare_png_rectangles(
    source: Path,
    width_mm: float,
    top_y: float,
) -> list[tuple[float, float, float, float]]:
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError(f"No visible pixels found in {source}")
    cropped = image.crop(bbox)
    target_width_px = round(width_mm / RASTER_PITCH_MM)
    target_height_px = max(
        1, round(target_width_px * cropped.height / cropped.width)
    )
    resized = cropped.resize(
        (target_width_px, target_height_px),
        Image.Resampling.LANCZOS,
    )

    actual_width = target_width_px * RASTER_PITCH_MM
    left = LOGO_CENTER_X - actual_width / 2
    top = top_y
    rectangles: list[tuple[float, float, float, float]] = []

    for y in range(target_height_px):
        run_start: int | None = None
        for x in range(target_width_px + 1):
            active = False
            if x < target_width_px:
                _, _, _, a = resized.getpixel((x, y))
                active = a >= 96
            if active and run_start is None:
                run_start = x
            if (not active or x == target_width_px) and run_start is not None:
                if x - run_start >= 1:
                    rectangles.append(
                        (
                            left + run_start * RASTER_PITCH_MM,
                            top + y * RASTER_PITCH_MM,
                            left + x * RASTER_PITCH_MM,
                            top + (y + 1) * RASTER_PITCH_MM,
                        )
                    )
                run_start = None
    return rectangles


def prepare_easyeda_rectangles() -> list[tuple[float, float, float, float]]:
    return prepare_png_rectangles(EASYEDA_PNG, EASYEDA_WIDTH, EASYEDA_TOP_Y)


def prepare_jlcpcb_rectangles() -> list[tuple[float, float, float, float]]:
    return prepare_png_rectangles(JLCPCB_PNG, JLCPCB_WIDTH, JLCPCB_TOP_Y)


def prepare_payload() -> dict[str, object]:
    return {
        "easyeda_rectangles": prepare_easyeda_rectangles(),
        "jlcpcb_rectangles": prepare_jlcpcb_rectangles(),
    }


def add_rectangle(
    board: pcbnew.BOARD,
    group: pcbnew.PCB_GROUP,
    rectangle: tuple[float, float, float, float],
) -> None:
    left, top, right, bottom = rectangle
    add_filled_contour(
        board,
        group,
        [
            (left, top),
            (right, top),
            (right, bottom),
            (left, bottom),
            (left, top),
        ],
        [],
    )


def apply_payload(payload_path: Path) -> None:
    global pcbnew
    import pcbnew

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    restored_segments = restore_border_segments(board)
    removed_items = remove_existing_group(board)

    group = pcbnew.PCB_GROUP(board)
    group.SetName(GROUP_NAME)
    board.Add(group)

    caption = pcbnew.PCB_TEXT(board)
    caption.SetText("Sponsored by")
    caption.SetPosition(point(LOGO_CENTER_X, CAPTION_Y))
    caption.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    caption.SetTextThickness(mm(0.15))
    caption.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    caption.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    caption.SetLayer(pcbnew.F_SilkS)
    board.Add(caption)
    group.AddItem(caption)

    easyeda_count = 0
    for rectangle in payload["easyeda_rectangles"]:
        add_rectangle(board, group, tuple(rectangle))
        easyeda_count += 1

    jlcpcb_count = 0
    for rectangle in payload["jlcpcb_rectangles"]:
        add_rectangle(board, group, tuple(rectangle))
        jlcpcb_count += 1

    pcbnew.SaveBoard(str(BOARD_PATH), board)
    payload_path.unlink(missing_ok=True)
    print(
        "Added sponsor logos: "
        f"removed {removed_items} old items, restored {restored_segments} "
        f"border segments, {easyeda_count} EasyEDA raster runs, "
        f"{jlcpcb_count} JLCPCB raster runs"
    )
    sys.stdout.flush()
    os._exit(0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.apply is not None:
        apply_payload(args.apply)
        return

    if not KICAD_PYTHON.exists():
        raise RuntimeError(f"KiCad Python was not found at {KICAD_PYTHON}")
    payload = prepare_payload()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        json.dump(payload, handle)
        payload_path = Path(handle.name)
    os.execv(
        str(KICAD_PYTHON),
        [
            str(KICAD_PYTHON),
            str(Path(__file__).resolve()),
            "--apply",
            str(payload_path),
        ],
    )


if __name__ == "__main__":
    main()
