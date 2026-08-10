#!/usr/bin/env python3
"""Build an EasyEDA Pro import package with line-hatched silkscreen artwork.

EasyEDA Pro's KiCad importer can preserve complex silkscreen outlines while
dropping the filled area of KiCad graphic polygons.  The manufacturing KiCad
project remains untouched; this script creates a derived import package where
top-level filled silkscreen polygons are replaced by dense graphic lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
import shutil
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[3]
SOURCE_PCB = ROOT / "hacking_box_v2.kicad_pcb"
RELEASE_ROOT = PROJECT_ROOT / "hardware" / "releases" / "rev3" / "easyeda-pro"
COMPAT_ROOT = RELEASE_ROOT / "silk-compat" / "hacking_badge_v3_easyeda_silk_compat"
UPLOAD_ZIP = RELEASE_ROOT / "upload" / "hacking_badge_v3_easyeda_pro_silk_compat_import.zip"
CHECKSUMS = RELEASE_ROOT / "SHA256SUMS.txt"

HATCH_PITCH_MM = 0.13
HATCH_WIDTH_MM = 0.15
MIN_SEGMENT_MM = 0.08


@dataclass(frozen=True)
class PolygonBlock:
    start: int
    end: int
    text: str
    layer: str
    points: tuple[tuple[float, float], ...]


def find_matching_paren(text: str, start: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise RuntimeError("Unbalanced KiCad PCB file")


def extract_silk_polygons(text: str) -> list[PolygonBlock]:
    blocks: list[PolygonBlock] = []
    for match in re.finditer(r"\n\t\(gr_poly\b", text):
        start = match.start() + 1
        end = find_matching_paren(text, start + 1)
        block = text[start:end]
        layer_match = re.search(r'\(layer "([FB]\.SilkS)"\)', block)
        if layer_match is None:
            continue
        if "(fill solid)" not in block and "(fill yes)" not in block:
            continue
        points = tuple(
            (float(x), float(y))
            for x, y in re.findall(
                r"\(xy\s+([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\)",
                block,
            )
        )
        if len(points) < 3:
            continue
        blocks.append(
            PolygonBlock(start, end, block, layer_match.group(1), points)
        )
    return blocks


def scanline_segments(
    points: tuple[tuple[float, float], ...],
) -> list[tuple[float, float, float, float]]:
    if points[0] != points[-1]:
        polygon = points + (points[0],)
    else:
        polygon = points

    min_y = min(y for _, y in polygon)
    max_y = max(y for _, y in polygon)
    first_y = math.floor(min_y / HATCH_PITCH_MM) * HATCH_PITCH_MM
    y = first_y
    segments: list[tuple[float, float, float, float]] = []
    while y <= max_y + HATCH_PITCH_MM:
        if y < min_y:
            y += HATCH_PITCH_MM
            continue
        intersections: list[float] = []
        for (x1, y1), (x2, y2) in zip(polygon, polygon[1:]):
            if y1 == y2:
                continue
            low = min(y1, y2)
            high = max(y1, y2)
            if not (low <= y < high):
                continue
            x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            intersections.append(x)
        intersections.sort()
        for x1, x2 in zip(intersections[0::2], intersections[1::2]):
            if x2 - x1 >= MIN_SEGMENT_MM:
                segments.append((x1, y, x2, y))
        y += HATCH_PITCH_MM
    return segments


def line_text(
    segment: tuple[float, float, float, float],
    layer: str,
) -> str:
    x1, y1, x2, y2 = segment
    return (
        "\t(gr_line\n"
        f"\t\t(start {x1:.6f} {y1:.6f})\n"
        f"\t\t(end {x2:.6f} {y2:.6f})\n"
        "\t\t(stroke\n"
        f"\t\t\t(width {HATCH_WIDTH_MM:.2f})\n"
        "\t\t\t(type solid)\n"
        "\t\t)\n"
        f"\t\t(layer \"{layer}\")\n"
        f"\t\t(uuid \"{uuid.uuid4()}\")\n"
        "\t)"
    )


def convert_pcb_silkscreen(text: str) -> tuple[str, int, int]:
    polygons = extract_silk_polygons(text)
    pieces: list[str] = []
    cursor = 0
    line_count = 0
    for polygon in polygons:
        pieces.append(text[cursor:polygon.start])
        segments = scanline_segments(polygon.points)
        pieces.append("\n".join(line_text(segment, polygon.layer) for segment in segments))
        line_count += len(segments)
        cursor = polygon.end
    pieces.append(text[cursor:])
    return "".join(pieces), len(polygons), line_count


def remove_editor_groups(text: str) -> tuple[str, int]:
    """Drop KiCad editor-only groups from the derived import board.

    Some logo artwork is grouped in KiCad.  After replacing grouped polygons
    with hatch lines, the old group references can point to deleted UUIDs.
    Groups are not manufacturing data, so removing them keeps the EasyEDA
    import package simple and avoids stale references.
    """

    pieces: list[str] = []
    cursor = 0
    group_count = 0
    for match in re.finditer(r"\n\t\(group\b", text):
        start = match.start() + 1
        end = find_matching_paren(text, start + 1)
        pieces.append(text[cursor:start])
        cursor = end
        group_count += 1
    pieces.append(text[cursor:])
    return "".join(pieces), group_count


def copy_project_files() -> None:
    if COMPAT_ROOT.exists():
        shutil.rmtree(COMPAT_ROOT)
    COMPAT_ROOT.mkdir(parents=True)

    for filename in (
        "hacking_box_v2.kicad_pro",
        "hacking_box_v2.kicad_sch",
        "sym-lib-table",
        "fp-lib-table",
        "hacking_box_v2-cache.lib",
    ):
        shutil.copy2(ROOT / filename, COMPAT_ROOT / filename)

    shutil.copytree(ROOT / "hacking_box_v2.pretty", COMPAT_ROOT / "hacking_box_v2.pretty")
    shutil.copytree(ROOT / "hacking_box_v2.3dshapes", COMPAT_ROOT / "hacking_box_v2.3dshapes")

    datasheet_dir = COMPAT_ROOT / "reference" / "datasheets"
    datasheet_dir.mkdir(parents=True)
    shutil.copy2(
        PROJECT_ROOT / "hardware" / "design" / "rev3" / "reference" / "datasheets" / "HS96L03W2C03.pdf",
        datasheet_dir / "HS96L03W2C03.pdf",
    )


def write_compat_pcb() -> tuple[int, int, int]:
    source = SOURCE_PCB.read_text(encoding="utf-8")
    converted, polygon_count, line_count = convert_pcb_silkscreen(source)
    converted, group_count = remove_editor_groups(converted)
    (COMPAT_ROOT / "hacking_box_v2.kicad_pcb").write_text(
        converted,
        encoding="utf-8",
    )
    return polygon_count, line_count, group_count


def zip_compat_project() -> None:
    UPLOAD_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if UPLOAD_ZIP.exists():
        UPLOAD_ZIP.unlink()
    with zipfile.ZipFile(UPLOAD_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(COMPAT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(COMPAT_ROOT.parent))


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_checksums() -> None:
    entries = {}
    if CHECKSUMS.exists():
        for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, name = line.split(maxsplit=1)
            entries[name] = digest
    relative = UPLOAD_ZIP.relative_to(RELEASE_ROOT).as_posix()
    entries[relative] = sha256(UPLOAD_ZIP)
    CHECKSUMS.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(entries.items())),
        encoding="utf-8",
    )


def main() -> None:
    copy_project_files()
    polygon_count, line_count, group_count = write_compat_pcb()
    zip_compat_project()
    update_checksums()
    print(
        f"Built EasyEDA silkscreen-compatible package: "
        f"{polygon_count} filled silk polygons -> {line_count} line segments, "
        f"removed {group_count} editor groups"
    )
    print(UPLOAD_ZIP)


if __name__ == "__main__":
    main()
