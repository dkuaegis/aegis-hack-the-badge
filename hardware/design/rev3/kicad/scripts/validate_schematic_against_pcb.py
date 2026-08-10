#!/usr/bin/env python3
"""Verify that the review schematic describes the routed PCB exactly."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
NETLIST_PATH = ROOT / "reports" / "hacking_box_v2_schematic.xml"
REPORT_PATH = ROOT / "reports" / "schematic-pcb-validation.txt"


def add_pin(
    mapping: dict[tuple[str, str], str],
    key: tuple[str, str],
    net_name: str,
    source: str,
) -> None:
    previous = mapping.get(key)
    if previous is not None and previous != net_name:
        raise RuntimeError(
            f"{source}: {key[0]} pin {key[1]} has both "
            f"{previous!r} and {net_name!r}"
        )
    mapping[key] = net_name


def pcb_data() -> tuple[
    dict[str, str],
    dict[tuple[str, str], str],
    set[tuple[str, str]],
]:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    values: dict[str, str] = {}
    connected: dict[tuple[str, str], str] = {}
    no_net: set[tuple[str, str]] = set()

    for footprint in board.GetFootprints():
        reference = footprint.GetReference()
        values[reference] = footprint.GetValue()
        for pad in footprint.Pads():
            pin = pad.GetNumber()
            if not pin:
                continue
            key = (reference, pin)
            net_name = pad.GetNetname()
            if net_name:
                add_pin(connected, key, net_name, "PCB")
                no_net.discard(key)
            elif key not in connected:
                no_net.add(key)

    return values, connected, no_net


def schematic_data() -> tuple[
    dict[str, str],
    dict[tuple[str, str], str],
    set[tuple[str, str]],
]:
    root = ET.parse(NETLIST_PATH).getroot()
    values = {
        component.attrib["ref"]: component.findtext("value", default="")
        for component in root.findall("./components/comp")
    }
    connected: dict[tuple[str, str], str] = {}
    no_net: set[tuple[str, str]] = set()

    for net in root.findall("./nets/net"):
        net_name = net.attrib["name"]
        is_no_connect = net_name.startswith("unconnected-(")
        for node in net.findall("node"):
            key = (node.attrib["ref"], node.attrib["pin"])
            if is_no_connect:
                no_net.add(key)
            else:
                add_pin(connected, key, net_name, "schematic")

    return values, connected, no_net


def mapping_differences(
    expected: dict[tuple[str, str], str],
    actual: dict[tuple[str, str], str],
) -> list[str]:
    differences: list[str] = []
    for key in sorted(set(expected) | set(actual)):
        expected_net = expected.get(key)
        actual_net = actual.get(key)
        if expected_net != actual_net:
            differences.append(
                f"{key[0]}.{key[1]}: PCB={expected_net!r}, "
                f"schematic={actual_net!r}"
            )
    return differences


def main() -> None:
    pcb_values, pcb_connected, pcb_no_net = pcb_data()
    sch_values, sch_connected, sch_no_net = schematic_data()

    ref_missing = sorted(set(pcb_values) - set(sch_values))
    ref_extra = sorted(set(sch_values) - set(pcb_values))
    value_mismatches = sorted(
        (
            reference,
            pcb_values[reference],
            sch_values[reference],
        )
        for reference in set(pcb_values) & set(sch_values)
        if pcb_values[reference] != sch_values[reference]
    )
    net_mismatches = mapping_differences(pcb_connected, sch_connected)
    no_net_missing = sorted(pcb_no_net - sch_no_net)
    no_net_extra = sorted(sch_no_net - pcb_no_net)

    passed = not any(
        (
            ref_missing,
            ref_extra,
            value_mismatches,
            net_mismatches,
            no_net_missing,
            no_net_extra,
        )
    )

    report = [
        "Hacking Badge V3 schematic-to-PCB validation",
        "================================================",
        f"Result: {'PASS' if passed else 'FAIL'}",
        f"PCB components: {len(pcb_values)}",
        f"Schematic components: {len(sch_values)}",
        f"PCB named nets: {len(set(pcb_connected.values()))}",
        f"Schematic named nets: {len(set(sch_connected.values()))}",
        f"Connected component-pin pairs checked: {len(pcb_connected)}",
        f"Intentional no-connect pins checked: {len(pcb_no_net)}",
        "",
        "Checks",
        "------",
        f"Reference set: {'PASS' if not ref_missing and not ref_extra else 'FAIL'}",
        f"Component values: {'PASS' if not value_mismatches else 'FAIL'}",
        f"Named pin-to-net mapping: {'PASS' if not net_mismatches else 'FAIL'}",
        (
            "Intentional no-connect mapping: "
            f"{'PASS' if not no_net_missing and not no_net_extra else 'FAIL'}"
        ),
    ]

    details = [
        ("Missing schematic references", ref_missing),
        ("Unexpected schematic references", ref_extra),
        (
            "Value mismatches",
            [
                f"{reference}: PCB={pcb_value!r}, schematic={sch_value!r}"
                for reference, pcb_value, sch_value in value_mismatches
            ],
        ),
        ("Pin-to-net mismatches", net_mismatches),
        (
            "PCB no-connect pins missing from schematic",
            [f"{reference}.{pin}" for reference, pin in no_net_missing],
        ),
        (
            "Unexpected schematic no-connect pins",
            [f"{reference}.{pin}" for reference, pin in no_net_extra],
        ),
    ]
    for heading, items in details:
        if items:
            report.extend(["", heading, "-" * len(heading), *items])

    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
