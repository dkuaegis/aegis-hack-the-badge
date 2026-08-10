#!/usr/bin/env python3
"""Validate the Rev.3 JLCPCB fabrication and assembly package."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
DEFAULT_RELEASE_DIR = ROOT.parents[2] / "releases" / "rev3" / "jlcpcb"

EXPECTED_ZIP_FILES = {
    "hacking_box_v2-F_Cu.gtl",
    "hacking_box_v2-B_Cu.gbl",
    "hacking_box_v2-F_Mask.gts",
    "hacking_box_v2-B_Mask.gbs",
    "hacking_box_v2-F_Paste.gtp",
    "hacking_box_v2-B_Paste.gbp",
    "hacking_box_v2-F_Silkscreen.gto",
    "hacking_box_v2-B_Silkscreen.gbo",
    "hacking_box_v2-Edge_Cuts.gm1",
    "hacking_box_v2-PTH.drl",
    "hacking_box_v2-NPTH.drl",
    "hacking_box_v2-job.gbrjob",
}

EXPECTED_JLCPCB_PLACEMENTS = {
    "J1": (62.5000, -100.9291, 0.0),
    "U1": (83.8733, -71.0000, 270.0),
    "U2": (34.5000, -56.5000, 180.0),
    "D1": (62.5000, -95.0000, 270.0),
    "Q_BZ": (91.0000, -48.0000, 270.0),
}


def split_designators(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=DEFAULT_RELEASE_DIR,
        help="Manufacturing release directory to validate.",
    )
    args = parser.parse_args()
    release_dir = args.release_dir.resolve()
    gerber_dir = release_dir / "fabrication" / "gerber"
    upload_dir = release_dir / "upload"
    assembly_dir = release_dir / "assembly"
    reports_dir = release_dir / "reports"
    zip_path = upload_dir / "hacking_badge_v3_jlcpcb_gerbers.zip"
    bom_path = upload_dir / "hacking_badge_v3_jlcpcb_bom.csv"
    cpl_path = upload_dir / "hacking_badge_v3_jlcpcb_cpl.csv"
    manual_path = assembly_dir / "hacking_badge_v3_manual_assembly.csv"
    report_path = reports_dir / "manufacturing_validation.txt"
    job_path = gerber_dir / "hacking_box_v2-job.gbrjob"

    checks: list[str] = []
    failures: list[str] = []

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        if names != EXPECTED_ZIP_FILES:
            failures.append(
                f"Gerber ZIP contents differ: {sorted(names ^ EXPECTED_ZIP_FILES)}"
            )
        else:
            checks.append("Gerber ZIP contains exactly 12 required files.")
        for info in archive.infolist():
            if info.file_size <= 100:
                failures.append(f"Suspiciously small file: {info.filename}")

    with job_path.open(encoding="utf-8") as source:
        job = json.load(source)
    specs = job["GeneralSpecs"]
    if specs["LayerNumber"] != 2:
        failures.append("Gerber job is not a 2-layer board.")
    if abs(specs["BoardThickness"] - 1.6) > 0.001:
        failures.append("Gerber job thickness is not 1.6 mm.")
    size = specs["Size"]
    if not (83.9 <= size["X"] <= 84.2 and 99.9 <= size["Y"] <= 100.2):
        failures.append(f"Unexpected board size: {size}")
    checks.append(
        f"Gerber job: 2 layers, {size['X']:.2f} x {size['Y']:.2f} mm, "
        f"{specs['BoardThickness']:.1f} mm thick."
    )

    edge_text = (gerber_dir / "hacking_box_v2-Edge_Cuts.gm1").read_text(
        encoding="ascii"
    )
    if "TF.FileFunction,Profile" not in edge_text or "M02*" not in edge_text:
        failures.append("Edge.Cuts Gerber has no valid profile/end marker.")
    else:
        checks.append("Board profile Gerber has profile metadata and end marker.")

    for drill_name in ("hacking_box_v2-PTH.drl", "hacking_box_v2-NPTH.drl"):
        drill_text = (gerber_dir / drill_name).read_text(encoding="ascii")
        if "M48" not in drill_text or "M30" not in drill_text:
            failures.append(f"Invalid Excellon structure: {drill_name}")
    checks.append("PTH and NPTH Excellon files contain valid headers/end markers.")

    drill_report = (reports_dir / "drill_report.txt").read_text(encoding="utf-8")
    if "0.200mm" not in drill_report:
        failures.append("Drill report does not contain the 0.20 mm minimum drill.")
    if "0.800mm" not in drill_report or "(with 4 slots)" not in drill_report:
        failures.append("Drill report does not contain four 0.80 mm plated slots.")
    checks.append("Drill report confirms 0.20 mm minimum drills and four 0.80 mm slots.")

    for silk_name in (
        "hacking_box_v2-F_Silkscreen.gto",
        "hacking_box_v2-B_Silkscreen.gbo",
    ):
        silk_text = (gerber_dir / silk_name).read_text(encoding="ascii")
        apertures = [
            float(match)
            for match in re.findall(r"%ADD\d+C,([0-9.]+)\*%", silk_text)
            if float(match) > 0
        ]
        if not apertures or min(apertures) < 0.15 - 1e-9:
            failures.append(f"Silkscreen aperture below 0.15 mm: {silk_name}")
    checks.append("Front and rear plotted silkscreen apertures are at least 0.15 mm.")

    board_text = BOARD_PATH.read_text(encoding="utf-8")
    sponsor_markers = (
        '(group "JLCPCB_SPONSOR_LOGO"',
        '(gr_text "Sponsored by"',
    )
    if not all(marker in board_text for marker in sponsor_markers):
        failures.append("Front EasyEDA/JLCPCB sponsor silkscreen group is missing.")
    else:
        checks.append("Front silkscreen contains the grouped EasyEDA/JLCPCB sponsor mark.")

    drc_text = (reports_dir / "drc_report.txt").read_text(encoding="utf-8")
    if "** Found 0 unconnected pads **" not in drc_text:
        failures.append("Final DRC report contains unconnected pads.")
    categories = set(re.findall(r"^\[([^]]+)\]", drc_text, flags=re.MULTILINE))
    unexpected_categories = categories - {"silk_edge_clearance", "silk_over_copper"}
    if unexpected_categories:
        failures.append(
            f"Unexpected final DRC categories: {sorted(unexpected_categories)}"
        )
    checks.append("Final DRC has no electrical, copper, drill, slot, or mask errors.")

    with bom_path.open(newline="", encoding="utf-8") as source:
        bom_rows = list(csv.DictReader(source))
    bom_refs: set[str] = set()
    for row in bom_rows:
        if not row["LCSC Part #"].startswith("C"):
            failures.append(f"Missing LCSC part: {row}")
        refs = split_designators(row["Designator"])
        if refs & bom_refs:
            failures.append(f"Duplicate BOM references: {sorted(refs & bom_refs)}")
        bom_refs.update(refs)

    with cpl_path.open(newline="", encoding="utf-8") as source:
        cpl_rows = list(csv.DictReader(source))
    cpl_refs = {row["Designator"] for row in cpl_rows}
    if bom_refs != cpl_refs:
        failures.append(f"BOM/CPL reference mismatch: {sorted(bom_refs ^ cpl_refs)}")
    if any(row["Layer"] != "Top" for row in cpl_rows):
        failures.append("CPL contains a bottom-side assembly placement.")
    cpl_y_values = [float(row["Mid Y"].removesuffix("mm")) for row in cpl_rows]
    if any(value >= 0 for value in cpl_y_values):
        failures.append(
            "CPL Y coordinates do not match KiCad's Gerber/position-file axis."
        )
    if "OLED1" in bom_refs or "OLED1" in cpl_refs:
        failures.append("OLED1 must be excluded from the JLCPCB BOM/CPL.")
    if len(cpl_rows) != 44:
        failures.append(f"Expected 44 CPL placements, found {len(cpl_rows)}.")
    cpl_by_reference = {row["Designator"]: row for row in cpl_rows}
    for reference, expected in EXPECTED_JLCPCB_PLACEMENTS.items():
        row = cpl_by_reference.get(reference)
        if row is None:
            failures.append(f"Missing corrected CPL placement: {reference}")
            continue
        actual = (
            float(row["Mid X"].removesuffix("mm")),
            float(row["Mid Y"].removesuffix("mm")),
            float(row["Rotation"]),
        )
        if any(abs(value - target) > 0.0001 for value, target in zip(actual, expected)):
            failures.append(
                f"Incorrect JLCPCB origin correction for {reference}: "
                f"expected {expected}, found {actual}"
            )
    checks.append(
        "J1, U1, U2, D1, and Q_BZ use verified LCSC placement corrections."
    )
    checks.append(
        f"Assembly package: {len(bom_rows)} BOM lines, "
        f"{len(cpl_rows)} unique top-side placements."
    )

    with manual_path.open(newline="", encoding="utf-8") as source:
        manual_rows = list(csv.DictReader(source))
    manual_refs = {row["Designator"] for row in manual_rows}
    if manual_refs != {"OLED1"}:
        failures.append(
            f"Manual assembly list must contain only OLED1: {sorted(manual_refs)}"
        )
    else:
        checks.append("Manual assembly list contains hand-soldered OLED1.")

    if failures:
        lines = ["FAIL"] + [f"- {item}" for item in failures]
    else:
        lines = ["PASS"] + [f"- {item}" for item in checks]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_path.read_text(encoding="utf-8"), end="")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
