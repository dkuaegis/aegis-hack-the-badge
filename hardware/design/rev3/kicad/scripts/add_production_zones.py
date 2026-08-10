#!/usr/bin/env python3
"""Add production copper zones in a fresh KiCad Python process."""

from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def rectangle(
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> pcbnew.SHAPE_POLY_SET:
    polygon = pcbnew.SHAPE_POLY_SET()
    outline = polygon.NewOutline()
    for x, y in (
        (left, top),
        (right, top),
        (right, bottom),
        (left, bottom),
    ):
        polygon.Append(point(x, y), outline)
    return polygon


def add_ground_zone(
    board: pcbnew.BOARD,
    gnd: pcbnew.NETINFO_ITEM,
    outline: pcbnew.SHAPE_POLY_SET,
    layer: int,
) -> None:
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(gnd)
    zone.SetOutline(outline)
    board.Add(zone)


def add_antenna_keepout(
    board: pcbnew.BOARD,
    outline: pcbnew.SHAPE_POLY_SET,
) -> None:
    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    keepout.SetLayerSet(layers)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowZoneFills(True)
    keepout.SetDoNotAllowPads(False)
    keepout.SetDoNotAllowFootprints(False)
    keepout.SetOutline(outline)
    board.Add(keepout)


def main() -> None:
    print("Loading routed board", flush=True)
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    existing_zones = list(board.Zones())
    copper_zones = [zone for zone in existing_zones if not zone.GetIsRuleArea()]
    if copper_zones:
        raise RuntimeError(
            "Board already has copper zones; run prepare_autoroute.py first"
        )
    print(
        f"Preserving {len(existing_zones)} routing keepouts",
        flush=True,
    )
    gnd = board.FindNet("GND")
    if gnd is None:
        raise RuntimeError("GND net is missing")

    for footprint in board.GetFootprints():
        if footprint.GetReference() == "J1":
            for pad in footprint.Pads():
                if pad.GetNumber() in {"A1", "B12", "SH"}:
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    # The fill engine clips this oversized polygon to the curved Edge.Cuts.
    # Keeping the source polygon simple also avoids a KiCad 10 macOS serializer
    # crash on complex imported shield outlines.
    front_outline = rectangle(15.0, 5.0, 110.0, 115.0)
    back_outline = rectangle(15.0, 5.0, 110.0, 115.0)

    print("Adding front GND zone", flush=True)
    add_ground_zone(board, gnd, front_outline, pcbnew.F_Cu)
    print("Adding back GND zone", flush=True)
    add_ground_zone(board, gnd, back_outline, pcbnew.B_Cu)
    print("Saving zoned board", flush=True)
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Added production zones: {BOARD_PATH}")


if __name__ == "__main__":
    main()
