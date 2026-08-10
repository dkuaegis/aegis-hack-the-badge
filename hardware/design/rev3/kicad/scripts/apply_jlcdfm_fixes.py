#!/usr/bin/env python3
"""Apply manufacturing hardening derived from the JLCDFM reports."""

from __future__ import annotations

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
    / "hacking_box_v3_pre_jlcdfm_2026-08-02.kicad_pcb"
)

MIN_ANNULAR_RING_MM = 0.20
MIN_SILK_WIDTH_MM = 0.15
MIN_VISIBLE_TEXT_MM = 1.00
SOLDER_MASK_EXPANSION_MM = 0.05
BLACK_MASK_MIN_WEB_MM = 0.13


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def point_mm(value: pcbnew.VECTOR2I) -> tuple[float, float]:
    return pcbnew.ToMM(value.x), pcbnew.ToMM(value.y)


def close(actual: tuple[float, float], expected: tuple[float, float]) -> bool:
    return all(abs(left - right) <= 0.01 for left, right in zip(actual, expected))


def segment_matches(
    segment: pcbnew.PCB_TRACK,
    start: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    actual_start = point_mm(segment.GetStart())
    actual_end = point_mm(segment.GetEnd())
    return (close(actual_start, start) and close(actual_end, end)) or (
        close(actual_start, end) and close(actual_end, start)
    )


def add_track_path(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    layer: int,
    width: int,
    coordinates: list[tuple[float, float]],
) -> None:
    for start, end in zip(coordinates, coordinates[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(point(*start))
        track.SetEnd(point(*end))
        track.SetLayer(layer)
        track.SetWidth(width)
        track.SetNet(net)
        board.Add(track)


def replace_sharp_branches(board: pcbnew.BOARD) -> int:
    replacements = [
        (
            "3V3",
            (28.0000, 53.0000),
            (30.2074, 55.2074),
            [
                (28.0000, 53.0000),
                (28.5000, 53.0000),
                (30.2074, 54.7074),
                (30.2074, 55.2074),
            ],
        ),
        (
            "3V3",
            (61.2300, 50.4300),
            (62.9156, 48.7444),
            [
                (61.2300, 50.4300),
                (61.7300, 50.4300),
                (62.9156, 49.2444),
                (62.9156, 48.7444),
            ],
        ),
        (
            "OLED_SDA",
            (66.3100, 50.4300),
            (49.7400, 67.0000),
            [
                (66.3100, 50.4300),
                (65.8100, 50.4300),
                (49.7400, 66.5000),
                (49.7400, 67.0000),
            ],
        ),
    ]
    replaced = 0
    nets = board.GetNetsByName()
    for net_name, start, end, path in replacements:
        for track in list(board.GetTracks()):
            if isinstance(track, pcbnew.PCB_VIA):
                continue
            if track.GetLayer() != pcbnew.B_Cu or track.GetNetname() != net_name:
                continue
            if not segment_matches(track, start, end):
                continue
            width = track.GetWidth()
            board.Remove(track)
            add_track_path(board, nets[net_name], pcbnew.B_Cu, width, path)
            replaced += 1
            break
    return replaced


def detour_front_border_around_c1(board: pcbnew.BOARD) -> int:
    """Route the decorative front border outside C1's mask openings."""
    targets = (
        ((27.007336, 51.319198), (26.380178, 53.718955)),
        ((26.380178, 53.718955), (25.668475, 56.633264)),
    )
    matched = []
    for item in board.GetDrawings():
        if (
            isinstance(item, pcbnew.PCB_SHAPE)
            and item.GetShape() == pcbnew.SHAPE_T_SEGMENT
            and item.GetLayer() == pcbnew.F_SilkS
            and any(segment_matches(item, start, end) for start, end in targets)
        ):
            matched.append(item)

    if len(matched) != len(targets):
        return 0

    width = matched[0].GetWidth()
    for item in matched:
        board.Remove(item)

    path = (
        (27.007336, 51.319198),
        (26.600000, 51.000000),
        (25.800000, 51.000000),
        (25.800000, 54.800000),
        (25.600000, 55.200000),
        (25.668475, 56.633264),
    )
    for start, end in zip(path, path[1:]):
        item = pcbnew.PCB_SHAPE(board)
        item.SetShape(pcbnew.SHAPE_T_SEGMENT)
        item.SetStart(point(*start))
        item.SetEnd(point(*end))
        item.SetWidth(width)
        item.SetLayer(pcbnew.F_SilkS)
        board.Add(item)
    return len(matched)


def harden_j1(footprint: pcbnew.FOOTPRINT) -> tuple[int, int, int]:
    duplicate_without_mask = {"B1", "B4", "B9", "B12"}
    duplicate_count = 0
    slot_count = 0
    peg_count = 0
    for pad in footprint.Pads():
        number = pad.GetNumber()
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            # Preserve the 0.20 mm fine-pitch copper spacing while overriding
            # the board-wide positive mask swell to a 1:1 J1 opening.
            pad.SetLocalSolderMaskMargin(mm(-SOLDER_MASK_EXPANSION_MM))
        if number in duplicate_without_mask:
            layers = pad.GetLayerSet()
            layers.RemoveLayer(pcbnew.F_Mask)
            layers.RemoveLayer(pcbnew.F_Paste)
            pad.SetLayerSet(layers)
            duplicate_count += 1

        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            pad.SetSize(pcbnew.VECTOR2I(mm(0.90), mm(0.90)))
            pad.SetDrillSize(pcbnew.VECTOR2I(mm(0.90), mm(0.90)))
            peg_count += 1

        drill = pad.GetDrillSize()
        if number != "SH" or drill.x == drill.y:
            continue
        new_length = 1.70 if pcbnew.ToMM(drill.y) > 1.4 else 1.60
        pad.SetDrillSize(pcbnew.VECTOR2I(mm(0.80), mm(new_length)))
        pad.SetSize(pcbnew.VECTOR2I(mm(1.30), mm(new_length + 0.50)))
        slot_count += 1
    return duplicate_count, slot_count, peg_count


def tent_u1_thermal_holes(footprint: pcbnew.FOOTPRINT) -> int:
    changed = 0
    for pad in footprint.Pads():
        if pad.GetNumber() != "41" or not pad.HasDrilledHole():
            continue
        layers = pad.GetLayerSet()
        layers.RemoveLayer(pcbnew.F_Mask)
        layers.RemoveLayer(pcbnew.B_Mask)
        pad.SetLayerSet(layers)
        changed += 1
    return changed


def move_nonessential_footprint_silk_to_fab(board: pcbnew.BOARD) -> int:
    """Keep assembly outlines in Fab without plotting them over pads/edges."""
    changed = 0
    for reference in ("J1", "BZ1"):
        footprint = board.FindFootprintByReference(reference)
        for item in footprint.GraphicalItems():
            if item.GetLayer() != pcbnew.F_SilkS:
                continue
            item.SetLayer(pcbnew.F_Fab)
            changed += 1
    return changed


def harden_silkscreen(board: pcbnew.BOARD) -> tuple[int, int]:
    shapes_changed = 0
    text_changed = 0
    items = list(board.GetDrawings())
    for footprint in board.GetFootprints():
        items.extend(footprint.GraphicalItems())

    for item in items:
        if item.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            continue
        if isinstance(item, pcbnew.PCB_SHAPE):
            width = item.GetWidth()
            if 0 < width < mm(MIN_SILK_WIDTH_MM):
                item.SetWidth(mm(MIN_SILK_WIDTH_MM))
                shapes_changed += 1
            continue
        if not isinstance(item, pcbnew.PCB_TEXT) or not item.IsVisible():
            continue
        if item.GetTextThickness() < mm(MIN_SILK_WIDTH_MM):
            item.SetTextThickness(mm(MIN_SILK_WIDTH_MM))
        width = pcbnew.ToMM(item.GetTextWidth())
        height = pcbnew.ToMM(item.GetTextHeight())
        if min(width, height) < MIN_VISIBLE_TEXT_MM:
            scale = MIN_VISIBLE_TEXT_MM / min(width, height)
            item.SetTextWidth(mm(width * scale))
            item.SetTextHeight(mm(height * scale))
        text_changed += 1
    return shapes_changed, text_changed


def main() -> None:
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_PATH.exists():
        shutil.copy2(BOARD_PATH, BACKUP_PATH)

    board = pcbnew.LoadBoard(str(BOARD_PATH))
    settings = board.GetDesignSettings()
    settings.m_SolderMaskExpansion = mm(SOLDER_MASK_EXPANSION_MM)
    settings.m_SolderMaskMinWidth = mm(BLACK_MASK_MIN_WEB_MM)
    plot_options = board.GetPlotOptions()
    plot_options.SetSubtractMaskFromSilk(True)
    plot_options.SetUseGerberProtelExtensions(True)
    plot_options.SetCreateGerberJobFile(True)
    plot_options.SetGerberPrecision(6)

    vias_changed = 0
    for item in board.GetTracks():
        if not isinstance(item, pcbnew.PCB_VIA):
            continue
        diameter = pcbnew.ToMM(item.GetWidth(pcbnew.F_Cu))
        # Use explicit finished drill sizes. Calculating 0.60 - 2 * 0.20
        # serialized as 0.199999 mm and tripped KiCad's 0.20 mm minimum.
        target_drill = 0.20 if diameter < 0.625 else 0.25
        target_drill_iu = round(target_drill * 1_000_000)
        if item.GetDrill() != target_drill_iu:
            # pcbnew.FromMM(0.20) can round down to 199999 internal units in
            # this KiCad build. Set the integer IU value so the saved board is
            # exactly on, rather than one nanometre below, the rule boundary.
            item.SetDrill(target_drill_iu)
            vias_changed += 1

    sharp_branches_changed = replace_sharp_branches(board)
    front_border_segments_replaced = detour_front_border_around_c1(board)
    duplicates_changed, slots_changed, pegs_changed = harden_j1(
        board.FindFootprintByReference("J1")
    )
    thermal_holes_tented = tent_u1_thermal_holes(
        board.FindFootprintByReference("U1")
    )
    footprint_silk_moved = move_nonessential_footprint_silk_to_fab(board)
    silk_shapes_changed, silk_text_changed = harden_silkscreen(board)

    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Sharp B.Cu branches reshaped: {sharp_branches_changed}", flush=True)
    print(
        f"Front border segments rerouted around C1: {front_border_segments_replaced}",
        flush=True,
    )
    print(f"Via drills reduced for >= 0.20 mm annular rings: {vias_changed}", flush=True)
    print(f"J1 duplicate mask/paste shapes removed: {duplicates_changed}", flush=True)
    print(f"J1 plated slots widened: {slots_changed}", flush=True)
    print(f"J1 alignment pegs enlarged: {pegs_changed}", flush=True)
    print(f"U1 thermal holes tented: {thermal_holes_tented}", flush=True)
    print(f"J1/BZ1 assembly outlines moved from Silk to Fab: {footprint_silk_moved}", flush=True)
    print(f"Silkscreen strokes widened: {silk_shapes_changed}", flush=True)
    print(f"Visible silkscreen texts hardened: {silk_text_changed}", flush=True)
    print(f"Saved: {BOARD_PATH}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
