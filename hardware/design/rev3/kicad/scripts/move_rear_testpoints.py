#!/usr/bin/env python3
from pathlib import Path

import pcbnew

import production_finalize as production


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
MOVE_Y_MM = 4.0
TRACK_WIDTH_MM = 0.25
VIA_DIAMETER_MM = 0.65
VIA_DRILL_MM = 0.30

TESTPOINT_POSITIONS = {
    "TP_3V3": (28.0, 53.0),
    "TP_GND": (34.0, 53.0),
    "TP_VBUS": (40.0, 53.0),
    "TP_EN": (28.0, 60.0),
    "TP_BOOT": (34.0, 60.0),
    "TP_UART_TX": (40.0, 60.0),
    "TP_UART_RX": (28.0, 67.0),
    "TP_OLED_SCL": (34.0, 67.0),
    "TP_OLED_SDA": (40.0, 67.0),
}

LABEL_POSITIONS = {
    "3V3": (28.0, 50.7),
    "GND": (34.0, 50.7),
    "5V": (40.0, 50.7),
    "EN": (28.0, 57.7),
    "BOOT": (34.0, 57.7),
    "TX": (40.0, 57.7),
    "RX": (28.0, 64.7),
    "SCL": (34.0, 64.7),
    "SDA": (40.0, 64.7),
}


def point(x_mm: float, y_mm: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


def same_position(first: pcbnew.VECTOR2I, second: pcbnew.VECTOR2I) -> bool:
    return first.x == second.x and first.y == second.y


def near_position(
    first: pcbnew.VECTOR2I,
    second: pcbnew.VECTOR2I,
    tolerance_nm: int = 1_000,
) -> bool:
    return (
        abs(first.x - second.x) <= tolerance_nm
        and abs(first.y - second.y) <= tolerance_nm
    )


def track_matches(
    track: pcbnew.PCB_TRACK,
    first: tuple[float, float],
    second: tuple[float, float],
) -> bool:
    start = track.GetStart()
    end = track.GetEnd()
    return (
        near_position(start, point(*first)) and near_position(end, point(*second))
    ) or (
        near_position(start, point(*second)) and near_position(end, point(*first))
    )


def find_track(
    board: pcbnew.BOARD,
    net_name: str,
    layer: int,
    first: tuple[float, float],
    second: tuple[float, float],
) -> pcbnew.PCB_TRACK:
    tracks = list(board.GetTracks())
    production.KEEPALIVE.extend(tracks)
    match = next(
        (
            track
            for track in tracks
            if type(track).__name__ == "PCB_TRACK"
            and track.GetNetname() == net_name
            and track.GetLayer() == layer
            and track_matches(track, first, second)
        ),
        None,
    )
    if match is None:
        candidates = [
            (
                (
                    pcbnew.ToMM(track.GetStart().x),
                    pcbnew.ToMM(track.GetStart().y),
                ),
                (
                    pcbnew.ToMM(track.GetEnd().x),
                    pcbnew.ToMM(track.GetEnd().y),
                ),
            )
            for track in tracks
            if type(track).__name__ == "PCB_TRACK"
            and track.GetNetname() == net_name
            and track.GetLayer() == layer
        ]
        raise RuntimeError(
            f"Could not find {net_name} track from {first} to {second}; "
            f"candidates: {candidates}"
        )
    return match


def add_track(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    layer: int,
    first: tuple[float, float],
    second: tuple[float, float],
) -> None:
    production.add_track_path(
        board,
        net,
        layer,
        TRACK_WIDTH_MM,
        [first, second],
    )


board = pcbnew.LoadBoard(str(BOARD_PATH))
footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}

for reference, (x_mm, y_mm) in TESTPOINT_POSITIONS.items():
    footprint = footprints[reference]
    old_position = point(x_mm, y_mm)
    if not same_position(footprint.GetPosition(), old_position):
        raise RuntimeError(f"{reference} must start at its original position")
    footprint.SetPosition(point(x_mm, y_mm + MOVE_Y_MM))

labels = {
    drawing.GetText(): drawing
    for drawing in board.GetDrawings()
    if type(drawing).__name__ == "PCB_TEXT"
    and drawing.GetLayerName() == "B.Silkscreen"
    and drawing.GetText() in LABEL_POSITIONS
}

for label, (x_mm, y_mm) in LABEL_POSITIONS.items():
    text = labels[label]
    old_position = point(x_mm, y_mm)
    if not same_position(text.GetPosition(), old_position):
        raise RuntimeError(f"{label} label must start at its original position")
    text.SetPosition(point(x_mm, y_mm + MOVE_Y_MM))

# The relocated TX pad occupies the old OLED SCL diagonal. Remove that one
# segment and let the clearance-aware router reconnect its original endpoints.
scl_gap = ((36.6055, 67.0), (45.0798, 58.5257))
scl_track = find_track(board, "OLED_SCL", pcbnew.B_Cu, *scl_gap)
scl_net = scl_track.GetNet()
board.Remove(scl_track)

production.CLEARANCE_MM = 0.50
router = production.GridRouter(board)

scl_start = production.grid_node(*scl_gap[0], production.B_LAYER)
scl_end = production.grid_node(*scl_gap[1], production.B_LAYER)
scl_path = router._route_to_tree("OLED_SCL", {scl_start}, scl_end)
router._emit(scl_path, scl_net, TRACK_WIDTH_MM)
router._reserve(scl_path, "OLED_SCL", TRACK_WIDTH_MM)
add_track(
    board,
    scl_net,
    pcbnew.B_Cu,
    scl_gap[0],
    production.node_xy(scl_start),
)
add_track(
    board,
    scl_net,
    pcbnew.B_Cu,
    scl_gap[1],
    production.node_xy(scl_end),
)

route_order = (
    "TP_UART_TX",
    "TP_BOOT",
    "TP_UART_RX",
    "TP_OLED_SCL",
    "TP_OLED_SDA",
    "TP_EN",
    "TP_3V3",
    "TP_GND",
    "TP_VBUS",
)
for reference in route_order:
    pad = next(iter(footprints[reference].Pads()))
    net = pad.GetNet()
    net_name = pad.GetNetname()
    target = production.terminal_for_pad(pad)
    tree = router.net_nodes[net_name]
    if not tree:
        raise RuntimeError(f"{reference} has no existing routed net")
    path = router._route_to_tree(net_name, tree, target)
    router._emit(path, net, TRACK_WIDTH_MM)
    router._reserve(path, net_name, TRACK_WIDTH_MM)
    router._connect_pad_to_grid(pad, target, net, TRACK_WIDTH_MM)

# Move layer-change vias away from the existing EN horizontal route. The
# router works on a 0.25 mm grid, so account for the actual 0.65 mm via body.
via_nudges = {
    ("PLAYER_UART_RX", 28.0, 67.5): (28.0, 67.0),
    ("OLED_SCL", 36.5, 67.5): (36.5, 67.0),
    ("OLED_SCL", 36.5, 68.75): (36.5, 69.0),
    ("OLED_SDA", 42.75, 67.5): (42.75, 67.0),
    ("OLED_SDA", 42.75, 68.75): (42.75, 69.0),
}
for (net_name, old_x, old_y), (new_x, new_y) in via_nudges.items():
    old_position = point(old_x, old_y)
    new_position = point(new_x, new_y)
    via = next(
        (
            item
            for item in board.GetTracks()
            if type(item).__name__ == "PCB_VIA"
            and item.GetNetname() == net_name
            and same_position(item.GetPosition(), old_position)
        ),
        None,
    )
    if via is None:
        raise RuntimeError(f"Could not find {net_name} via at {old_x}, {old_y}")
    for track in board.GetTracks():
        if type(track).__name__ != "PCB_TRACK" or track.GetNetname() != net_name:
            continue
        if same_position(track.GetStart(), old_position):
            track.SetStart(new_position)
        if same_position(track.GetEnd(), old_position):
            track.SetEnd(new_position)
    via.SetPosition(new_position)

# Remove the original pad stubs superseded by the local routes.
stale_tracks = (
    ("VBUS", (40.0, 53.0), (37.4214, 55.5786)),
    ("EN", (26.8858, 61.1142), (28.0, 60.0)),
    ("BOOT_GPIO0", (34.0, 60.0), (32.8974, 58.8974)),
    ("OLED_SCL", (34.0, 67.0), (36.6055, 67.0)),
    ("OLED_SDA", (49.74, 67.0), (40.0, 67.0)),
)
stale_items = [
    find_track(board, net_name, pcbnew.B_Cu, first, second)
    for net_name, first, second in stale_tracks
]
for stale_item in stale_items:
    board.Remove(stale_item)

# Terminate each new branch on an exact existing junction rather than relying
# on overlapping copper to imply connectivity.
vbus_branch = find_track(
    board,
    "VBUS",
    pcbnew.B_Cu,
    (37.5, 55.5),
    (37.5, 57.0),
)
if same_position(vbus_branch.GetStart(), point(37.5, 55.5)):
    vbus_branch.SetStart(point(37.4214, 55.5786))
else:
    vbus_branch.SetEnd(point(37.4214, 55.5786))

en_trunk = find_track(
    board,
    "EN",
    pcbnew.B_Cu,
    (26.8858, 61.1142),
    (26.8858, 67.4507),
)
en_net = en_trunk.GetNet()
board.Remove(en_trunk)
add_track(
    board,
    en_net,
    pcbnew.B_Cu,
    (26.8858, 64.0),
    (26.8858, 67.4507),
)
en_branch = find_track(
    board,
    "EN",
    pcbnew.B_Cu,
    (27.0, 64.0),
    (28.0, 64.0),
)
if same_position(en_branch.GetStart(), point(27.0, 64.0)):
    en_branch.SetStart(point(26.8858, 64.0))
else:
    en_branch.SetEnd(point(26.8858, 64.0))

boot_trunk = find_track(
    board,
    "BOOT_GPIO0",
    pcbnew.B_Cu,
    (32.8974, 58.8974),
    (27.5435, 58.8974),
)
boot_net = boot_trunk.GetNet()
board.Remove(boot_trunk)
add_track(
    board,
    boot_net,
    pcbnew.B_Cu,
    (31.5, 58.8974),
    (27.5435, 58.8974),
)
boot_branch = find_track(
    board,
    "BOOT_GPIO0",
    pcbnew.B_Cu,
    (31.5, 59.0),
    (31.5, 62.25),
)
if same_position(boot_branch.GetStart(), point(31.5, 59.0)):
    boot_branch.SetStart(point(31.5, 58.8974))
else:
    boot_branch.SetEnd(point(31.5, 58.8974))

sda_net = board.FindNet("OLED_SDA")
add_track(
    board,
    sda_net,
    pcbnew.B_Cu,
    (49.74, 67.0),
    (42.75, 67.0),
)

# OLED1 was moved upward earlier. Its former PTH pad had also served as the
# layer transition for 3V3, so retain that electrical junction with a via.
legacy_3v3_junction = point(61.23, 50.43)
if not any(
    type(item).__name__ == "PCB_VIA"
    and item.GetNetname() == "3V3"
    and same_position(item.GetPosition(), legacy_3v3_junction)
    for item in board.GetTracks()
):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(legacy_3v3_junction)
    via.SetWidth(pcbnew.FromMM(VIA_DIAMETER_MM))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL_MM))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(board.FindNet("3V3"))
    board.Add(via)

pcbnew.SaveBoard(str(BOARD_PATH), board)
