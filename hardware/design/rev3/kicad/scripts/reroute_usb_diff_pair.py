#!/usr/bin/env python3
"""Replace the legacy USB routing with a compact, length-matched pair."""

from __future__ import annotations

import math
import os
import shutil
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
BACKUP_PATH = (
    ROOT.parents[3]
    / "archive"
    / "design"
    / "rev3-development"
    / "pcb-revisions"
    / "hacking_box_v3_pre_usb_diff_pair_2026-08-02.kicad_pcb"
)

TRACK_WIDTH_MM = 0.20
VIA_DIAMETER_MM = 0.65
VIA_DRILL_MM = 0.30
POWER_TRACK_WIDTH_MM = 0.25
COORD_TOLERANCE_MM = 0.01


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def position_mm(item: pcbnew.BOARD_ITEM) -> tuple[float, float]:
    pos = item.GetPosition()
    return pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)


def endpoint_mm(track: pcbnew.PCB_TRACK) -> tuple[float, float]:
    end = track.GetEnd()
    return pcbnew.ToMM(end.x), pcbnew.ToMM(end.y)


def coordinates_match(
    actual: tuple[float, float], expected: tuple[float, float]
) -> bool:
    return all(
        abs(actual_value - expected_value) <= COORD_TOLERANCE_MM
        for actual_value, expected_value in zip(actual, expected)
    )


def segment_matches(
    track: pcbnew.PCB_TRACK,
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    actual_start = position_mm(track)
    actual_end = endpoint_mm(track)
    return (
        coordinates_match(actual_start, start)
        and coordinates_match(actual_end, end)
    ) or (
        coordinates_match(actual_start, end)
        and coordinates_match(actual_end, start)
    )


def add_track_path(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    layer: int,
    width_mm: float,
    coordinates: list[tuple[float, float]],
) -> None:
    for start, end in zip(coordinates, coordinates[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(point(*start))
        track.SetEnd(point(*end))
        track.SetLayer(layer)
        track.SetWidth(mm(width_mm))
        track.SetNet(net)
        board.Add(track)


def add_via(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    coordinate: tuple[float, float],
) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(point(*coordinate))
    via.SetWidth(mm(VIA_DIAMETER_MM))
    via.SetDrill(mm(VIA_DRILL_MM))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetNet(net)
    board.Add(via)


def path_length(coordinates: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(coordinates, coordinates[1:])
    )


def main() -> None:
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_PATH.exists():
        shutil.copy2(BOARD_PATH, BACKUP_PATH)

    board = pcbnew.LoadBoard(str(BOARD_PATH))
    nets = board.GetNetsByName()
    d_minus = nets["USB_D_N"]
    d_plus = nets["USB_D_P"]
    vbus = nets["VBUS"]

    usb_items = [
        item
        for item in board.GetTracks()
        if item.GetNetname() in {"USB_D_N", "USB_D_P"}
    ]
    for item in usb_items:
        board.Remove(item)

    replaceable_vbus_segments = [
        ((63.6375, 95.0), (64.1198, 95.0)),
        ((64.1198, 95.0), (64.8060, 95.6862)),
        ((64.8060, 95.6862), (64.8060, 96.9571)),
        ((63.6375, 95.0), (64.5000, 95.0)),
        ((64.5000, 95.0), (64.8060, 96.9571)),
    ]
    for item in list(board.GetTracks()):
        if item.GetNetname() != "VBUS":
            continue
        if isinstance(item, pcbnew.PCB_VIA):
            if coordinates_match(position_mm(item), (64.5000, 95.0)):
                board.Remove(item)
            continue
        if any(
            segment_matches(item, start, end)
            for start, end in replaceable_vbus_segments
        ):
            board.Remove(item)

    # Move this short VBUS branch to B.Cu so D+ can approach D1 unobstructed.
    new_vbus_via = (64.50, 95.00)
    old_vbus_via = (64.8060, 96.9571)
    add_track_path(
        board,
        vbus,
        pcbnew.F_Cu,
        POWER_TRACK_WIDTH_MM,
        [(63.6375, 95.00), new_vbus_via],
    )
    add_via(board, vbus, new_vbus_via)
    add_track_path(
        board,
        vbus,
        pcbnew.B_Cu,
        POWER_TRACK_WIDTH_MM,
        [new_vbus_via, old_vbus_via],
    )

    # The pair exits below the ESP32, fans out only for the two vias, and then
    # crosses the otherwise empty central area on B.Cu. This preserves the
    # existing LED/button routing and avoids all front-side artwork keepouts.
    d_minus_source = [
        (77.52, 62.25),
        (77.85, 62.58),
        (77.85, 78.00),
        (78.05, 78.20),
    ]
    d_plus_source = [
        (76.25, 62.25),
        (76.25, 63.10),
        (77.10, 63.95),
        (77.35, 64.20),
        (77.35, 78.00),
        (77.15, 78.20),
    ]
    d_minus_back = [
        (78.05, 78.20),
        (77.85, 78.40),
        (68.00, 88.25),
        (68.00, 92.50),
        (68.00, 94.10),
        (68.50, 94.60),
    ]
    d_plus_back = [
        (77.15, 78.20),
        (77.35, 78.40),
        (67.50, 88.25),
        (67.50, 92.50),
        (67.50, 95.45),
        (67.00, 95.95),
    ]
    d_minus_finish = [
        (68.50, 94.60),
        (67.95, 94.05),
        (63.6375, 94.05),
    ]
    d_plus_finish = [(67.00, 95.95), (63.6375, 95.95)]

    add_track_path(
        board, d_minus, pcbnew.F_Cu, TRACK_WIDTH_MM, d_minus_source
    )
    add_track_path(board, d_plus, pcbnew.F_Cu, TRACK_WIDTH_MM, d_plus_source)
    add_via(board, d_minus, d_minus_source[-1])
    add_via(board, d_plus, d_plus_source[-1])
    add_track_path(board, d_minus, pcbnew.B_Cu, TRACK_WIDTH_MM, d_minus_back)
    add_track_path(board, d_plus, pcbnew.B_Cu, TRACK_WIDTH_MM, d_plus_back)
    add_via(board, d_minus, d_minus_back[-1])
    add_via(board, d_plus, d_plus_back[-1])
    add_track_path(
        board, d_minus, pcbnew.F_Cu, TRACK_WIDTH_MM, d_minus_finish
    )
    add_track_path(board, d_plus, pcbnew.F_Cu, TRACK_WIDTH_MM, d_plus_finish)

    # Bridge both flow-through sides of D1 and branch toward the USB-C pads.
    # The interleaved D+ connector pads use the same compact B.Cu bridge that
    # previously passed DRC, while the D- branch leaves its T at 45 degrees.
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        TRACK_WIDTH_MM,
        [(63.6375, 94.05), (62.25, 94.05), (61.3625, 94.05)],
    )
    d_minus_connector = [
        (62.25, 94.05),
        (62.6519, 94.4519),
        (62.6519, 97.4326),
        (62.75, 97.5307),
        (62.75, 98.455),
    ]
    d_minus_duplicate = [
        (62.75, 98.455),
        (62.75, 99.2962),
        (62.5263, 99.5199),
        (61.9812, 99.5199),
        (61.75, 99.2887),
        (61.75, 98.455),
    ]
    add_track_path(
        board, d_minus, pcbnew.F_Cu, TRACK_WIDTH_MM, d_minus_connector
    )
    add_track_path(
        board, d_minus, pcbnew.F_Cu, TRACK_WIDTH_MM, d_minus_duplicate
    )

    d_plus_left_via = (62.0005, 96.7916)
    d_plus_right_via = (63.3011, 96.7916)
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        TRACK_WIDTH_MM,
        [(61.3625, 95.95), (62.0005, 96.5880), d_plus_left_via],
    )
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        TRACK_WIDTH_MM,
        [(63.6375, 95.95), (63.3011, 96.2864), d_plus_right_via],
    )
    add_via(board, d_plus, d_plus_left_via)
    add_via(board, d_plus, d_plus_right_via)
    add_track_path(
        board,
        d_plus,
        pcbnew.B_Cu,
        TRACK_WIDTH_MM,
        [d_plus_left_via, d_plus_right_via],
    )
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        TRACK_WIDTH_MM,
        [d_plus_left_via, (62.25, 97.0411), (62.25, 98.455)],
    )
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        TRACK_WIDTH_MM,
        [d_plus_right_via, (63.25, 96.8427), (63.25, 98.455)],
    )

    pcbnew.SaveBoard(str(BOARD_PATH), board)

    minus_length = sum(
        path_length(path)
        for path in (d_minus_source, d_minus_back, d_minus_finish)
    )
    plus_length = sum(
        path_length(path)
        for path in (d_plus_source, d_plus_back, d_plus_finish)
    )
    print(f"Removed {len(usb_items)} legacy USB track/via items", flush=True)
    print(f"U1-D1 D- length: {minus_length:.3f} mm", flush=True)
    print(f"U1-D1 D+ length: {plus_length:.3f} mm", flush=True)
    print(
        f"U1-D1 pair mismatch: {abs(minus_length - plus_length):.3f} mm",
        flush=True,
    )
    print(f"Saved: {BOARD_PATH}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
