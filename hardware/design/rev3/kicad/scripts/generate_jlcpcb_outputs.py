#!/usr/bin/env python3
"""Generate validated JLCPCB BOM and CPL files from the production PCB."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
RELEASE_DIR = ROOT.parents[2] / "releases" / "rev3" / "jlcpcb"
UPLOAD_DIR = RELEASE_DIR / "upload"
ASSEMBLY_DIR = RELEASE_DIR / "assembly"
BOM_PATH = UPLOAD_DIR / "hacking_badge_v3_jlcpcb_bom.csv"
CPL_PATH = UPLOAD_DIR / "hacking_badge_v3_jlcpcb_cpl.csv"
MANUAL_PATH = ASSEMBLY_DIR / "hacking_badge_v3_manual_assembly.csv"
BATCH_QUANTITY = 5


@dataclass(frozen=True)
class PartGroup:
    comment: str
    footprint: str
    lcsc: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class PlacementCorrection:
    x_mm: float = 0.0
    y_mm: float = 0.0
    rotation_degrees: float = 0.0


# JLCPCB renders these LCSC packages around their EasyEDA library origins,
# which differ from the KiCad footprint anchors. These offsets were solved by
# matching each library package pad to the corresponding production PCB pad.
JLCPCB_PLACEMENT_CORRECTIONS = {
    "J1": PlacementCorrection(y_mm=1.5709),
    "U1": PlacementCorrection(x_mm=-3.6267),
    "U2": PlacementCorrection(rotation_degrees=180.0),
    "D1": PlacementCorrection(rotation_degrees=270.0),
    "Q_BZ": PlacementCorrection(rotation_degrees=180.0),
}


PART_GROUPS = (
    PartGroup(
        "ESP32-S3-WROOM-1-N8R8",
        "ESP32-S3-WROOM-1",
        "C2913201",
        ("U1",),
    ),
    PartGroup("AMS1117-3.3", "SOT-223", "C6186", ("U2",)),
    PartGroup(
        "TYPE-C-31-M-12",
        "USB-C 16P",
        "C165948",
        ("J1",),
    ),
    PartGroup("USBLC6-2SC6", "SOT-23-6", "C2827654", ("D1",)),
    PartGroup("SMD5020-ZK", "SMD 5.3x5.3mm", "C49246955", ("BZ1",)),
    PartGroup("AO3400A", "SOT-23", "C20917", ("Q_BZ",)),
    PartGroup("1N4148W", "SOD-123", "C917030", ("D_BZ",)),
    PartGroup(
        "10uF",
        "0805",
        "C15850",
        ("C1", "C3", "C4", "C5", "C7", "C9"),
    ),
    PartGroup(
        "100nF",
        "0603",
        "C14663",
        ("C2", "C6", "C8", "C_OLED"),
    ),
    PartGroup("1uF", "0603", "C15849", ("C_EN",)),
    PartGroup("5.1k", "0603", "C23186", ("R1", "R2")),
    PartGroup(
        "10k",
        "0603",
        "C25804",
        ("R_BOOT", "R_BZ_PD", "R_EN", "R_SCL", "R_SDA"),
    ),
    PartGroup(
        "1k",
        "0603",
        "C21190",
        (
            "R_BZ",
            "R_CHAL0",
            "R_CHAL1",
            "R_CHAL2",
            "R_LED1",
            "R_LED2",
            "R_LED3",
            "R_LED4",
            "R_LED5",
            "R_UART_RX",
            "R_UART_TX",
        ),
    ),
    PartGroup(
        "KT-0603R red",
        "LED 0603",
        "C2286",
        ("LED1", "LED2", "LED3", "LED4", "LED5"),
    ),
    PartGroup(
        "TS-1088-AR02016 game controls",
        "SMD 4x3mm",
        "C720477",
        ("SW_ADMIN", "SW_BOOT", "SW_EN"),
    ),
)


def main() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ASSEMBLY_DIR.mkdir(parents=True, exist_ok=True)
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}

    assembled: dict[str, PartGroup] = {}
    for group in PART_GROUPS:
        for reference in group.references:
            if reference in assembled:
                raise RuntimeError(f"Duplicate BOM reference: {reference}")
            if reference not in footprints:
                raise RuntimeError(f"BOM reference not on PCB: {reference}")
            assembled[reference] = group

    with BOM_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            ("Comment", "Designator", "Footprint", "LCSC Part #")
        )
        for group in PART_GROUPS:
            writer.writerow(
                (
                    group.comment,
                    ",".join(group.references),
                    group.footprint,
                    group.lcsc,
                )
            )

    with CPL_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("Designator", "Mid X", "Mid Y", "Layer", "Rotation"))
        for reference in sorted(assembled):
            footprint = footprints[reference]
            position = footprint.GetPosition()
            side = "Bottom" if footprint.IsFlipped() else "Top"
            correction = JLCPCB_PLACEMENT_CORRECTIONS.get(
                reference, PlacementCorrection()
            )
            x_mm = pcbnew.ToMM(position.x) + correction.x_mm
            y_mm = -pcbnew.ToMM(position.y) + correction.y_mm
            rotation = (
                footprint.GetOrientationDegrees()
                + correction.rotation_degrees
            ) % 360
            writer.writerow(
                (
                    reference,
                    f"{x_mm:.4f}mm",
                    # KiCad Gerbers and the official position exporter use an
                    # upward-positive manufacturing Y axis. pcbnew's board
                    # API exposes the editor's downward-positive Y axis.
                    f"{y_mm:.4f}mm",
                    side,
                    f"{rotation:.2f}",
                )
            )

    with MANUAL_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "Designator",
                "Qty per board",
                f"Qty for {BATCH_QUANTITY} boards",
                "Recommended order qty",
                "Part",
                "Supplier",
                "Supplier item",
                "Assembly",
                "Notes",
            )
        )
        writer.writerow(
            (
                "OLED1",
                1,
                BATCH_QUANTITY,
                BATCH_QUANTITY + 1,
                "HS96L03W2C03",
                "DeviceMart",
                "15963242",
                "Hand solder",
                (
                    "Pin 1 GND, 2 VCC, 3 SCL, 4 SDA; use a straight "
                    "1x4 2.54mm male header if the module ships without one"
                ),
            )
        )

    print(f"Generated BOM with {len(PART_GROUPS)} lines: {BOM_PATH}")
    print(f"Generated CPL with {len(assembled)} placements: {CPL_PATH}")
    print(f"Generated manual assembly list: {MANUAL_PATH}")


if __name__ == "__main__":
    main()
