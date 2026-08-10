#!/usr/bin/env python3
"""Cut the supplied MSG CTF logo out of the rear Aegis silkscreen."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
PROJECT_ROOT = ROOT.parents[3]
SOURCE_PNG = (
    PROJECT_ROOT / "assets" / "brand" / "msg-ctf" / "msg-ctf-logo.png"
)
SOURCE_SVG = (
    PROJECT_ROOT / "assets" / "brand" / "aegis" / "black-white-ring.svg"
)
KICAD_PYTHON = Path(
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
    "Python.framework/Versions/Current/bin/python3"
)

LOGO_CENTER_X = 62.5
LOGO_CENTER_Y = 86.0
LOGO_WIDTH_MM = 30.0
RASTER_PITCH_MM = 0.10
ALPHA_CROP_THRESHOLD = 32
ALPHA_MASK_THRESHOLD = 64
MIN_COMPONENT_PIXELS = 5

BOARD_CENTER_X = 62.5
BOARD_TOP = 10.0
BOARD_WIDTH = 84.0
BOARD_HEIGHT = 100.0
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def sample_svg_path(
    path_data: str,
    curve_steps: int = 10,
) -> list[tuple[float, float]]:
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
            cursor = absolute(read_number(), read_number(), relative)
            start = cursor
            points.append(cursor)
            command = "l" if relative else "L"
            last_control = None
        elif operation == "l":
            cursor = absolute(read_number(), read_number(), relative)
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
        elif operation in ("c", "s"):
            if operation == "s":
                if previous_command in ("c", "s") and last_control is not None:
                    first = (
                        2 * cursor[0] - last_control[0],
                        2 * cursor[1] - last_control[1],
                    )
                else:
                    first = cursor
            else:
                first = absolute(read_number(), read_number(), relative)
            second = absolute(read_number(), read_number(), relative)
            end = absolute(read_number(), read_number(), relative)
            origin = cursor
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                u = 1.0 - t
                points.append(
                    (
                        u**3 * origin[0]
                        + 3 * u**2 * t * first[0]
                        + 3 * u * t**2 * second[0]
                        + t**3 * end[0],
                        u**3 * origin[1]
                        + 3 * u**2 * t * first[1]
                        + 3 * u * t**2 * second[1]
                        + t**3 * end[1],
                    )
                )
            cursor = end
            last_control = second
        else:
            raise ValueError(f"Unsupported SVG path command: {command}")
        previous_command = operation

    return points


def bounds(
    points: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    xs = [item[0] for item in points]
    ys = [item[1] for item in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_rear_silhouette() -> list[tuple[float, float]]:
    svg = SOURCE_SVG.read_text(encoding="utf-8")
    entries = re.findall(r'<path\s+d="([^"]+)"([^>]*)>', svg)
    sampled = [(sample_svg_path(path_data), attrs) for path_data, attrs in entries]
    shield_index = next(
        index
        for index, (_, attrs) in enumerate(sampled)
        if 'fill="#040000"' in attrs and 'stroke="#070102"' in attrs
    )
    shield = sampled[shield_index][0]
    silhouette = max(
        (points for points, _ in sampled[shield_index + 1 :]),
        key=lambda points: (
            (bounds(points)[2] - bounds(points)[0])
            * (bounds(points)[3] - bounds(points)[1])
        ),
    )

    min_x, min_y, max_x, max_y = bounds(shield)
    scale_x = BOARD_WIDTH / (max_x - min_x)
    scale_y = BOARD_HEIGHT / (max_y - min_y)
    left = BOARD_CENTER_X - BOARD_WIDTH / 2
    return [
        (
            left + (x - min_x) * scale_x,
            BOARD_TOP + (y - min_y) * scale_y,
        )
        for x, y in silhouette
    ]


def remove_pixel_noise(mask: list[list[bool]]) -> None:
    height = len(mask)
    width = len(mask[0])
    seen: set[tuple[int, int]] = set()

    for start_y in range(height):
        for start_x in range(width):
            if not mask[start_y][start_x] or (start_x, start_y) in seen:
                continue
            stack = [(start_x, start_y)]
            component: list[tuple[int, int]] = []
            seen.add((start_x, start_y))
            while stack:
                x, y = stack.pop()
                component.append((x, y))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        neighbor = (x + dx, y + dy)
                        nx, ny = neighbor
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        if neighbor in seen or not mask[ny][nx]:
                            continue
                        seen.add(neighbor)
                        stack.append(neighbor)
            if len(component) < MIN_COMPONENT_PIXELS:
                for x, y in component:
                    mask[y][x] = False


def merge_row_runs(mask: list[list[bool]]) -> list[list[int]]:
    height = len(mask)
    width = len(mask[0])
    rectangles: list[list[int]] = []
    active: dict[tuple[int, int], int] = {}

    for y in range(height + 1):
        runs: set[tuple[int, int]] = set()
        if y < height:
            x = 0
            while x < width:
                if not mask[y][x]:
                    x += 1
                    continue
                start = x
                while x < width and mask[y][x]:
                    x += 1
                runs.add((start, x))

        for run, start_y in list(active.items()):
            if run not in runs:
                rectangles.append([run[0], start_y, run[1], y])
                del active[run]
        for run in runs:
            active.setdefault(run, y)

    return rectangles


def prepare_mask() -> dict[str, object]:
    from PIL import Image, ImageFilter

    alpha = Image.open(SOURCE_PNG).convert("RGBA").getchannel("A")
    crop_mask = alpha.point(
        lambda value: 255 if value >= ALPHA_CROP_THRESHOLD else 0
    )
    crop_box = crop_mask.getbbox()
    if crop_box is None:
        raise RuntimeError(f"No visible artwork found in {SOURCE_PNG}")

    cropped = alpha.crop(crop_box)
    target_width = max(1, round(LOGO_WIDTH_MM / RASTER_PITCH_MM))
    target_height = max(
        1,
        round(target_width * cropped.height / cropped.width),
    )
    resized = cropped.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    ).filter(ImageFilter.MaxFilter(3))
    pixels = list(resized.get_flattened_data())
    mask = [
        [
            pixels[y * target_width + x] >= ALPHA_MASK_THRESHOLD
            for x in range(target_width)
        ]
        for y in range(target_height)
    ]
    remove_pixel_noise(mask)
    rectangles = merge_row_runs(mask)
    return {
        "width_px": target_width,
        "height_px": target_height,
        "rectangles": rectangles,
        "crop_box": list(crop_box),
    }


def apply_knockout(mask_path: Path) -> None:
    import pcbnew

    def mm(value: float) -> int:
        return pcbnew.FromMM(value)

    def point(x: float, y: float) -> pcbnew.VECTOR2I:
        return pcbnew.VECTOR2I(mm(x), mm(y))

    payload = json.loads(mask_path.read_text(encoding="utf-8"))
    width_px = int(payload["width_px"])
    height_px = int(payload["height_px"])
    rectangles = payload["rectangles"]
    pitch = LOGO_WIDTH_MM / width_px
    logo_height = height_px * pitch
    right = LOGO_CENTER_X + LOGO_WIDTH_MM / 2
    top = LOGO_CENTER_Y - logo_height / 2

    # Rear artwork is mirrored in board coordinates so it reads normally
    # when the finished PCB is viewed from the back.
    cutout = pcbnew.SHAPE_POLY_SET()
    for x0, y0, x1, y1 in rectangles:
        board_x0 = right - x1 * pitch
        board_x1 = right - x0 * pitch
        board_y0 = top + y0 * pitch
        board_y1 = top + y1 * pitch
        outline = cutout.NewOutline()
        for x, y in (
            (board_x0, board_y0),
            (board_x1, board_y0),
            (board_x1, board_y1),
            (board_x0, board_y1),
        ):
            cutout.Append(point(x, y), outline)
    cutout.Simplify()

    board = pcbnew.LoadBoard(str(BOARD_PATH))
    rear_polygons = [
        item
        for item in board.GetDrawings()
        if isinstance(item, pcbnew.PCB_SHAPE)
        and item.GetLayer() == pcbnew.B_SilkS
        and item.GetShape() == pcbnew.SHAPE_T_POLY
        and item.IsSolidFill()
    ]
    if not rear_polygons:
        raise RuntimeError("Rear Aegis silkscreen polygons were not found")

    artwork = pcbnew.SHAPE_POLY_SET()
    silhouette_outline = artwork.NewOutline()
    silhouette = load_rear_silhouette()
    for x, y in silhouette[:-1] if silhouette[0] == silhouette[-1] else silhouette:
        artwork.Append(point(x, y), silhouette_outline)
    area_before = artwork.Area()
    artwork.BooleanSubtract(cutout)
    artwork.Simplify()
    area_after = artwork.Area()
    if area_after >= area_before:
        raise RuntimeError("MSG CTF mask did not intersect the rear silkscreen")

    for item in rear_polygons:
        board.Remove(item)

    artwork.Fracture(True)
    polygon_count = 0
    for outline_index in range(artwork.OutlineCount()):
        source = artwork.COutline(outline_index)
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
        item.SetLayer(pcbnew.B_SilkS)
        board.Add(item)
        polygon_count += 1

    pcbnew.SaveBoard(str(BOARD_PATH), board)
    mask_path.unlink(missing_ok=True)
    print(
        f"Added rear MSG CTF knockout: {LOGO_WIDTH_MM:.1f} x "
        f"{logo_height:.1f} mm, {len(rectangles)} raster runs, "
        f"{polygon_count} rear silkscreen polygons"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.apply is not None:
        apply_knockout(args.apply)
        return

    if not KICAD_PYTHON.exists():
        raise RuntimeError(f"KiCad Python was not found at {KICAD_PYTHON}")
    payload = prepare_mask()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        json.dump(payload, handle)
        mask_path = Path(handle.name)
    os.execv(
        str(KICAD_PYTHON),
        [
            str(KICAD_PYTHON),
            str(Path(__file__).resolve()),
            "--apply",
            str(mask_path),
        ],
    )


if __name__ == "__main__":
    main()
