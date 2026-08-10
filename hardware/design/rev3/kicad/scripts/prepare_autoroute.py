#!/usr/bin/env python3
"""Prepare the production placement and export a Specctra DSN file."""

from pathlib import Path
import os

import pcbnew
import wx

import production_finalize as production


ROOT = Path(__file__).resolve().parents[1]
AUTOROUTE_DIR = (
    ROOT.parents[3]
    / "archive"
    / "design"
    / "rev3-development"
    / "autoroute"
)
UNROUTED_BOARD = AUTOROUTE_DIR / "hacking_box_v3_unrouted.kicad_pcb"
DSN_PATH = AUTOROUTE_DIR / "hacking_box_v3.dsn"


def add_route_keepout(
    board: pcbnew.BOARD,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    both_layers: bool = False,
    block_zone_fill: bool = False,
) -> None:
    keepout = pcbnew.ZONE(board)
    keepout.SetIsRuleArea(True)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    if both_layers:
        layers.AddLayer(pcbnew.B_Cu)
    keepout.SetLayerSet(layers)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowZoneFills(block_zone_fill)
    keepout.SetDoNotAllowPads(False)
    keepout.SetDoNotAllowFootprints(False)
    outline = production.rectangle_poly(left, top, right, bottom)
    keepout.SetOutline(outline)
    board.Add(keepout)
    # KiCad 10's macOS SWIG bindings retain native pointers to these objects.
    production.KEEPALIVE.extend((layers, outline, keepout))


def add_production_route_keepouts(board: pcbnew.BOARD) -> None:
    # The antenna requires a copper-free volume on both layers.
    add_route_keepout(
        board,
        95.4,
        59.7,
        104.0,
        82.3,
        both_layers=True,
        block_zone_fill=True,
    )

    # Keep front-layer routing away from visible silkscreen artwork. Ground
    # pours remain allowed so the mask has a visually uniform background.
    front_artwork_boxes = (
        (49.0, 16.0, 76.0, 24.0),  # event title and developer credit
        (32.0, 26.4, 37.0, 28.6),  # UART label
        (56.0, 53.8, 69.0, 56.7),  # STATUS and LED numbers
        (53.8, 62.8, 71.2, 80.2),  # complete circular Aegis logo
        (50.2, 82.1, 54.8, 85.5),  # <-
        (60.2, 82.1, 64.8, 85.5),  # OK
        (70.2, 82.1, 74.8, 85.5),  # ->
        (58.8, 90.8, 66.2, 92.8),  # USB-C
    )
    for box in front_artwork_boxes:
        add_route_keepout(board, *box)


def main() -> None:
    app = wx.App(False)
    print("Loading production board", flush=True)
    AUTOROUTE_DIR.mkdir(exist_ok=True)
    board = pcbnew.LoadBoard(str(production.BOARD_PATH))
    print("Removing existing routing and zones", flush=True)
    production.remove_routing_and_zones(board)
    print("Applying production placement and buzzer circuit", flush=True)
    production.replace_power_and_add_buzzer(board)
    parts = production.footprint_map(board)
    print("Assigning production nets", flush=True)
    production.assign_board_nets(board, parts)
    print("Adding routing keepouts for antenna and front artwork", flush=True)
    add_production_route_keepouts(board)
    print("Saving unrouted KiCad board", flush=True)
    pcbnew.SaveBoard(str(UNROUTED_BOARD), board)
    print("Exporting Specctra DSN", flush=True)
    if not pcbnew.ExportSpecctraDSN(board, str(DSN_PATH)):
        raise RuntimeError(f"Specctra DSN export failed: {DSN_PATH}")

    print(f"Saved unrouted board: {UNROUTED_BOARD}")
    print(f"Exported Specctra DSN: {DSN_PATH}")
    # KiCad 10's macOS SWIG wrappers can crash while destructing board items
    # in a standalone process. All outputs are flushed before this clean exit.
    os._exit(0)


if __name__ == "__main__":
    main()
