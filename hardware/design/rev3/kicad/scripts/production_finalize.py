#!/usr/bin/env python3
"""Build the electrically connected Hacking Badge V3 production PCB.

The compact layout script owns the board outline, artwork, and the original
component placement. This script adds the approved production parts, assigns
all nets, routes the two-layer board, and fills the ground planes.
"""

from __future__ import annotations

from collections import defaultdict
from heapq import heappop, heappush
from pathlib import Path
import math

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
LOCAL_LIBRARY = ROOT / "hacking_box_v2.pretty"
KICAD_FOOTPRINTS = Path(
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
)

GRID_MM = 0.25
EDGE_MARGIN_MM = 0.65
SIGNAL_WIDTH_MM = 0.25
POWER_WIDTH_MM = 0.65
VBUS_WIDTH_MM = 0.8
VIA_DIAMETER_MM = 0.65
VIA_DRILL_MM = 0.3
CLEARANCE_MM = 0.2

F_LAYER = 0
B_LAYER = 1
LAYER_ID = {F_LAYER: pcbnew.F_Cu, B_LAYER: pcbnew.B_Cu}

# KiCad 10's standalone macOS SWIG bindings invalidate container proxies when
# their Python wrappers are collected without a wx.App. Retain every board-item
# wrapper until the board has been saved.
KEEPALIVE: list[object] = []


def mm(value: float) -> int:
    return pcbnew.FromMM(value)


def point(x: float, y: float) -> pcbnew.VECTOR2I:
    return pcbnew.VECTOR2I(mm(x), mm(y))


def pos_mm(item) -> tuple[float, float]:
    position = item.GetPosition()
    return pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)


def place(
    footprint: pcbnew.FOOTPRINT,
    x: float,
    y: float,
    angle: float = 0.0,
) -> None:
    footprint.SetPosition(point(x, y))
    footprint.SetOrientationDegrees(angle)


def load_footprint(library: Path, name: str) -> pcbnew.FOOTPRINT:
    footprint = pcbnew.FootprintLoad(str(library), name)
    if footprint is None:
        raise RuntimeError(f"Could not load footprint {library.name}:{name}")
    return footprint


def add_part(
    board: pcbnew.BOARD,
    library: Path,
    footprint_name: str,
    reference: str,
    value: str,
    x: float,
    y: float,
    angle: float = 0.0,
) -> pcbnew.FOOTPRINT:
    footprint = load_footprint(library, footprint_name)
    footprint.SetReference(reference)
    footprint.SetValue(value)
    place(footprint, x, y, angle)
    board.Add(footprint)
    return footprint


def footprint_map(board: pcbnew.BOARD) -> dict[str, pcbnew.FOOTPRINT]:
    return {fp.GetReference(): fp for fp in all_footprints(board)}


def all_footprints(board: pcbnew.BOARD) -> list[pcbnew.FOOTPRINT]:
    footprints = board.GetFootprints()
    KEEPALIVE.extend(footprints)
    return footprints


def all_pads(footprint: pcbnew.FOOTPRINT) -> list[pcbnew.PAD]:
    footprint_pads = footprint.Pads()
    KEEPALIVE.extend(footprint_pads)
    return footprint_pads


def remove_routing_and_zones(board: pcbnew.BOARD) -> None:
    tracks = list(board.GetTracks())
    KEEPALIVE.extend(tracks)
    for track in tracks:
        board.Remove(track)
    zones = list(board.Zones())
    KEEPALIVE.extend(zones)
    for zone in zones:
        board.Remove(zone)


def remove_generated_parts(board: pcbnew.BOARD) -> None:
    generated = {"BZ1", "Q_BZ", "D_BZ", "R_BZ", "R_BZ_PD", "C9"}
    for footprint in all_footprints(board):
        if footprint.GetReference() in generated:
            board.Remove(footprint)


def remove_generated_text(board: pcbnew.BOARD) -> None:
    # Board-drawing iteration is not exposed consistently by KiCad 10's
    # standalone Python bindings. Production annotations live in footprints
    # and the rule area instead, so there is nothing to remove here.
    return


def replace_critical_modules(board: pcbnew.BOARD) -> None:
    """Restore unmodified production footprints at the approved locations."""
    parts = footprint_map(board)
    for reference in ("U1", "J1"):
        if reference in parts:
            board.Remove(parts[reference])

    esp = add_part(
        board,
        KICAD_FOOTPRINTS / "RF_Module.pretty",
        "ESP32-S3-WROOM-1",
        "U1",
        "ESP32-S3-WROOM-1-N8R8",
        87.5,
        71.0,
        -90,
    )
    usb = add_part(
        board,
        KICAD_FOOTPRINTS / "Connector_USB.pretty",
        "USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        "J1",
        "TYPE-C-31-M-12",
        62.5,
        102.5,
        0,
    )
    esp.Reference().SetVisible(False)
    usb.Reference().SetVisible(False)


def set_production_constraints(board: pcbnew.BOARD) -> None:
    settings = board.GetDesignSettings()
    settings.m_TrackMinWidth = mm(0.15)
    settings.m_MinThroughDrill = mm(0.2)
    settings.m_HoleToHoleMin = mm(0.2)


def add_text(
    board: pcbnew.BOARD,
    text: str,
    x: float,
    y: float,
    size: float,
    thickness: float,
    layer: int = pcbnew.F_SilkS,
) -> None:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(point(x, y))
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    item.SetLayer(layer)
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(item)


def ensure_net(board: pcbnew.BOARD, name: str) -> pcbnew.NETINFO_ITEM:
    existing = board.FindNet(name)
    if existing is not None:
        return existing
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def pads(footprint: pcbnew.FOOTPRINT, number: str) -> list[pcbnew.PAD]:
    matches = [
        pad for pad in all_pads(footprint) if pad.GetNumber() == str(number)
    ]
    if not matches:
        raise RuntimeError(
            f"{footprint.GetReference()} has no pad {number}"
        )
    return matches


def assign(
    parts: dict[str, pcbnew.FOOTPRINT],
    nets: dict[str, pcbnew.NETINFO_ITEM],
    net_name: str,
    reference: str,
    pad_number: str,
) -> None:
    if reference not in parts:
        raise RuntimeError(f"Missing footprint {reference}")
    for pad in pads(parts[reference], pad_number):
        pad.SetNet(nets[net_name])


def assign_board_nets(
    board: pcbnew.BOARD,
    parts: dict[str, pcbnew.FOOTPRINT],
) -> dict[str, pcbnew.NETINFO_ITEM]:
    for footprint in all_footprints(board):
        for pad in all_pads(footprint):
            pad.SetNetCode(0)

    names = [
        "GND",
        "VBUS",
        "3V3",
        "USB_D_N",
        "USB_D_P",
        "USB_CC1",
        "USB_CC2",
        "EN",
        "BOOT_GPIO0",
        "OLED_SDA",
        "OLED_SCL",
        "GAME_LEFT",
        "GAME_OK",
        "GAME_RIGHT",
        "STATUS_LED_1_MCU",
        "STATUS_LED_2_MCU",
        "STATUS_LED_3_MCU",
        "STATUS_LED_4_MCU",
        "STATUS_LED_5_MCU",
        "STATUS_LED_1_A",
        "STATUS_LED_2_A",
        "STATUS_LED_3_A",
        "STATUS_LED_4_A",
        "STATUS_LED_5_A",
        "UART_TX_MCU",
        "UART_RX_MCU",
        "PLAYER_UART_TX",
        "PLAYER_UART_RX",
        "CHAL_0_MCU",
        "CHAL_1_MCU",
        "CHAL_2_MCU",
        "CHAL_0",
        "CHAL_1",
        "CHAL_2",
        "BUZZER_GPIO",
        "BUZZER_GATE",
        "BUZZER_SW",
    ]
    nets = {name: ensure_net(board, name) for name in names}

    assignments: dict[str, list[tuple[str, str]]] = {
        "GND": [
            ("U1", "1"),
            ("U1", "40"),
            ("U1", "41"),
            ("U2", "1"),
            ("J1", "A1"),
            ("J1", "A12"),
            ("J1", "B1"),
            ("J1", "B12"),
            ("J1", "SH"),
            ("D1", "2"),
            ("R1", "2"),
            ("R2", "2"),
            ("OLED1", "1"),
            ("P_UART", "1"),
            ("SW_EN", "2"),
            ("SW_BOOT", "2"),
            ("SW_ADMIN", "2"),
            ("Q_BZ", "2"),
            ("R_BZ_PD", "2"),
            ("TP_GND", "1"),
        ],
        "VBUS": [
            ("J1", "A4"),
            ("J1", "A9"),
            ("J1", "B4"),
            ("J1", "B9"),
            ("D1", "5"),
            ("U2", "3"),
            ("C1", "1"),
            ("C2", "1"),
            ("C3", "1"),
            ("TP_VBUS", "1"),
        ],
        "3V3": [
            ("U1", "2"),
            ("U2", "2"),
            ("C4", "1"),
            ("C5", "1"),
            ("C6", "1"),
            ("C7", "1"),
            ("C8", "1"),
            ("C9", "1"),
            ("C_OLED", "1"),
            ("R_EN", "1"),
            ("R_BOOT", "1"),
            ("R_SCL", "1"),
            ("R_SDA", "1"),
            ("OLED1", "2"),
            ("P_UART", "2"),
            ("BZ1", "1"),
            ("D_BZ", "1"),
            ("TP_3V3", "1"),
        ],
        "USB_D_N": [
            ("U1", "13"),
            ("J1", "A7"),
            ("J1", "B7"),
            ("D1", "1"),
            ("D1", "6"),
        ],
        "USB_D_P": [
            ("U1", "14"),
            ("J1", "A6"),
            ("J1", "B6"),
            ("D1", "3"),
            ("D1", "4"),
        ],
        "USB_CC1": [("J1", "A5"), ("R1", "1")],
        "USB_CC2": [("J1", "B5"), ("R2", "1")],
        "EN": [
            ("U1", "3"),
            ("R_EN", "2"),
            ("C_EN", "1"),
            ("TP_EN", "1"),
        ],
        "BOOT_GPIO0": [
            ("U1", "27"),
            ("R_BOOT", "2"),
            ("TP_BOOT", "1"),
        ],
        "OLED_SDA": [
            ("U1", "4"),
            ("OLED1", "4"),
            ("R_SDA", "2"),
            ("TP_OLED_SDA", "1"),
        ],
        "OLED_SCL": [
            ("U1", "5"),
            ("OLED1", "3"),
            ("R_SCL", "2"),
            ("TP_OLED_SCL", "1"),
        ],
        # ESP32-S3-WROOM-1 module pads 17, 18, and 20 are GPIO9, GPIO10,
        # and GPIO12 respectively. EN and GPIO0 remain on staff test pads.
        "GAME_LEFT": [("U1", "17"), ("SW_EN", "1")],
        "GAME_OK": [("U1", "18"), ("SW_BOOT", "1")],
        "GAME_RIGHT": [("U1", "20"), ("SW_ADMIN", "1")],
        "STATUS_LED_1_MCU": [("U1", "21"), ("R_LED1", "1")],
        "STATUS_LED_2_MCU": [("U1", "22"), ("R_LED2", "1")],
        "STATUS_LED_3_MCU": [("U1", "8"), ("R_LED3", "1")],
        "STATUS_LED_4_MCU": [("U1", "9"), ("R_LED4", "1")],
        "STATUS_LED_5_MCU": [("U1", "10"), ("R_LED5", "1")],
        "STATUS_LED_1_A": [("R_LED1", "2"), ("LED1", "2")],
        "STATUS_LED_2_A": [("R_LED2", "2"), ("LED2", "2")],
        "STATUS_LED_3_A": [("R_LED3", "2"), ("LED3", "2")],
        "STATUS_LED_4_A": [("R_LED4", "2"), ("LED4", "2")],
        "STATUS_LED_5_A": [("R_LED5", "2"), ("LED5", "2")],
        "UART_TX_MCU": [("U1", "37"), ("R_UART_TX", "1")],
        "UART_RX_MCU": [("U1", "36"), ("R_UART_RX", "1")],
        "PLAYER_UART_TX": [
            ("R_UART_TX", "2"),
            ("P_UART", "3"),
            ("TP_UART_TX", "1"),
        ],
        "PLAYER_UART_RX": [
            ("R_UART_RX", "2"),
            ("P_UART", "4"),
            ("TP_UART_RX", "1"),
        ],
        "CHAL_0_MCU": [("U1", "6"), ("R_CHAL0", "1")],
        "CHAL_1_MCU": [("U1", "7"), ("R_CHAL1", "1")],
        "CHAL_2_MCU": [("U1", "12"), ("R_CHAL2", "1")],
        "CHAL_0": [("R_CHAL0", "2"), ("P_CHAL0", "1")],
        "CHAL_1": [("R_CHAL1", "2"), ("P_CHAL1", "1")],
        "CHAL_2": [("R_CHAL2", "2"), ("P_CHAL2", "1")],
        "BUZZER_GPIO": [("U1", "11"), ("R_BZ", "1")],
        "BUZZER_GATE": [
            ("R_BZ", "2"),
            ("R_BZ_PD", "1"),
            ("Q_BZ", "1"),
        ],
        "BUZZER_SW": [("BZ1", "2"), ("Q_BZ", "3"), ("D_BZ", "2")],
    }

    for index in range(1, 6):
        assignments["GND"].append((f"LED{index}", "1"))
    for capacitor in (
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C9",
        "C_EN",
        "C_OLED",
    ):
        assignments["GND"].append((capacitor, "2"))

    for net_name, members in assignments.items():
        for reference, pad_number in members:
            assign(parts, nets, net_name, reference, pad_number)

    return nets


def replace_power_and_add_buzzer(board: pcbnew.BOARD) -> None:
    remove_generated_parts(board)
    replace_critical_modules(board)
    set_production_constraints(board)
    parts = footprint_map(board)

    if "U2" in parts:
        board.Remove(parts["U2"])

    package_library = KICAD_FOOTPRINTS / "Package_TO_SOT_SMD.pretty"
    resistor_library = KICAD_FOOTPRINTS / "Resistor_SMD.pretty"
    capacitor_library = KICAD_FOOTPRINTS / "Capacitor_SMD.pretty"
    diode_library = KICAD_FOOTPRINTS / "Diode_SMD.pretty"

    add_part(
        board,
        package_library,
        "SOT-223-3_TabPin2",
        "U2",
        "AMS1117-3.3",
        34.5,
        56.5,
        0,
    )
    add_part(
        board,
        LOCAL_LIBRARY,
        "Buzzer_SMD5020_ZK",
        "BZ1",
        "SMD5020-ZK",
        90.0,
        41.5,
        0,
    )
    add_part(
        board,
        package_library,
        "SOT-23",
        "Q_BZ",
        "AO3400A",
        91.0,
        48.0,
        90,
    )
    add_part(
        board,
        diode_library,
        "D_SOD-123",
        "D_BZ",
        "1N4148W",
        88.0,
        47.0,
        90,
    )
    add_part(
        board,
        resistor_library,
        "R_0603_1608Metric",
        "R_BZ",
        "1k",
        82.5,
        46.5,
        0,
    )
    add_part(
        board,
        resistor_library,
        "R_0603_1608Metric",
        "R_BZ_PD",
        "10k",
        82.5,
        49.5,
        0,
    )
    add_part(
        board,
        capacitor_library,
        "C_0805_2012Metric",
        "C9",
        "10uF",
        92.0,
        52.0,
        90,
    )

    # Open up the original regulator cluster around the larger SOT-223 body.
    revised_layout = {
        "C1": (27.0, 53.0, 90),
        "C2": (27.0, 56.5, 90),
        "C3": (27.0, 60.0, 90),
        "C4": (42.0, 53.0, 90),
        "C5": (42.0, 56.5, 90),
        "C6": (42.0, 60.0, 90),
    }
    parts = footprint_map(board)
    for reference, (x, y, angle) in revised_layout.items():
        place(parts[reference], x, y, angle)

    remove_generated_text(board)


Node = tuple[int, int, int]


def grid_node(x: float, y: float, layer: int) -> Node:
    return round(x / GRID_MM), round(y / GRID_MM), layer


def node_xy(node: Node) -> tuple[float, float]:
    return node[0] * GRID_MM, node[1] * GRID_MM


def iter_grid_box(
    left: float,
    top: float,
    right: float,
    bottom: float,
):
    for ix in range(
        math.floor(left / GRID_MM),
        math.ceil(right / GRID_MM) + 1,
    ):
        for iy in range(
            math.floor(top / GRID_MM),
            math.ceil(bottom / GRID_MM) + 1,
        ):
            yield ix, iy


def pad_layers(pad: pcbnew.PAD) -> list[int]:
    result: list[int] = []
    if pad.IsOnLayer(pcbnew.F_Cu):
        result.append(F_LAYER)
    if pad.IsOnLayer(pcbnew.B_Cu):
        result.append(B_LAYER)
    return result


def terminal_for_pad(pad: pcbnew.PAD) -> Node:
    layers = pad_layers(pad)
    if not layers:
        raise RuntimeError("Pad has no copper layer")
    # Through-hole and back-side test pads start on B.Cu to keep the front clean.
    preferred = B_LAYER if B_LAYER in layers else F_LAYER
    x, y = pos_mm(pad)
    return grid_node(x, y, preferred)


def add_track_path(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    layer: int,
    width: float,
    coordinates: list[tuple[float, float]],
) -> None:
    for start, end in zip(coordinates, coordinates[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(point(*start))
        track.SetEnd(point(*end))
        track.SetLayer(layer)
        track.SetWidth(mm(width))
        track.SetNet(net)
        board.Add(track)


def add_via(
    board: pcbnew.BOARD,
    net: pcbnew.NETINFO_ITEM,
    x: float,
    y: float,
) -> None:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(point(x, y))
    via.SetWidth(mm(VIA_DIAMETER_MM))
    via.SetDrill(mm(VIA_DRILL_MM))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetNet(net)
    board.Add(via)


def route_usb_pair_manually(
    board: pcbnew.BOARD,
    nets: dict[str, pcbnew.NETINFO_ITEM],
) -> None:
    width = 0.2
    d_minus = nets["USB_D_N"]
    d_plus = nets["USB_D_P"]

    # USB-C D- duplicate pads: one escapes on F.Cu, the interleaved pad
    # crosses beneath the connector on B.Cu before joining the same branch.
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        width,
        [
            (61.75, 100.455),
            (61.75, 99.5),
            (60.75, 98.5),
            (60.75, 94.05),
            (61.3625, 94.05),
        ],
    )
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        width,
        [(62.75, 100.455), (62.75, 102.0)],
    )
    add_via(board, d_minus, 62.75, 102.0)
    add_track_path(
        board,
        d_minus,
        pcbnew.B_Cu,
        width,
        [(62.75, 102.0), (60.0, 102.0), (60.0, 98.5)],
    )
    add_via(board, d_minus, 60.0, 98.5)
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        width,
        [(60.0, 98.5), (60.75, 98.5)],
    )

    # USB-C D+ duplicate pads can join on F.Cu because D- has already
    # changed layers at the crossing.
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        width,
        [
            (62.25, 100.455),
            (62.25, 99.25),
            (63.25, 99.25),
            (64.0, 98.5),
            (64.0, 97.0),
            (61.0, 97.0),
            (61.3625, 95.95),
        ],
    )
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        width,
        [(63.25, 100.455), (63.25, 99.25)],
    )

    # Short each flow-through channel under the USBLC6 package.
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        width,
        [(61.3625, 94.05), (63.6375, 94.05)],
    )
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        width,
        [(61.3625, 95.95), (63.6375, 95.95)],
    )

    # The protected pair runs in parallel on B.Cu, then escapes directly
    # into ESP32-S3 GPIO19/GPIO20 on F.Cu.
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        width,
        [(63.6375, 94.05), (66.5, 93.5)],
    )
    add_via(board, d_minus, 66.5, 93.5)
    add_track_path(
        board,
        d_minus,
        pcbnew.B_Cu,
        width,
        [(66.5, 93.5), (66.5, 59.5), (77.5, 59.5)],
    )
    add_via(board, d_minus, 77.5, 59.5)
    add_track_path(
        board,
        d_minus,
        pcbnew.F_Cu,
        width,
        [(77.5, 59.5), (77.52, 62.25)],
    )

    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        width,
        [(63.6375, 95.95), (67.25, 96.5)],
    )
    add_via(board, d_plus, 67.25, 96.5)
    add_track_path(
        board,
        d_plus,
        pcbnew.B_Cu,
        width,
        [(67.25, 96.5), (67.25, 60.5), (76.25, 60.5)],
    )
    add_via(board, d_plus, 76.25, 60.5)
    add_track_path(
        board,
        d_plus,
        pcbnew.F_Cu,
        width,
        [(76.25, 60.5), (76.25, 62.25)],
    )


def route_led_anodes_manually(
    board: pcbnew.BOARD,
    nets: dict[str, pcbnew.NETINFO_ITEM],
    parts: dict[str, pcbnew.FOOTPRINT],
) -> None:
    for index in range(1, 6):
        resistor_pad = pads(parts[f"R_LED{index}"], "2")[0]
        led_pad = pads(parts[f"LED{index}"], "2")[0]
        rx, ry = pos_mm(resistor_pad)
        lx, ly = pos_mm(led_pad)
        bend_y = 59.75
        add_track_path(
            board,
            nets[f"STATUS_LED_{index}_A"],
            pcbnew.F_Cu,
            SIGNAL_WIDTH_MM,
            [(rx, ry), (rx, bend_y), (lx, bend_y), (lx, ly)],
        )


class GridRouter:
    def __init__(self, board: pcbnew.BOARD) -> None:
        self.board = board
        self.outline = pcbnew.SHAPE_POLY_SET()
        if not board.GetBoardPolygonOutlines(self.outline, False):
            raise RuntimeError("Invalid board outline")
        self.inside_cache: dict[tuple[int, int], bool] = {}
        self.pad_blocked: list[dict[tuple[int, int], set[str]]] = [
            defaultdict(set),
            defaultdict(set),
        ]
        self.via_forbidden: set[tuple[int, int]] = set()
        self.occupied: list[dict[tuple[int, int], str]] = [{}, {}]
        self.net_nodes: dict[str, set[Node]] = defaultdict(set)
        self.terminal_escape: dict[str, set[Node]] = defaultdict(set)
        self.antenna_rect = (95.4, 59.7, 104.0, 82.3)
        self._build_static_obstacles()
        self._build_terminal_escapes()
        self._seed_existing_routing()

    def _inside(self, ix: int, iy: int) -> bool:
        key = (ix, iy)
        if key in self.inside_cache:
            return self.inside_cache[key]
        x = ix * GRID_MM
        y = iy * GRID_MM
        probes = (
            (x, y),
            (x - EDGE_MARGIN_MM, y),
            (x + EDGE_MARGIN_MM, y),
            (x, y - EDGE_MARGIN_MM),
            (x, y + EDGE_MARGIN_MM),
        )
        valid = all(self.outline.Contains(point(px, py)) for px, py in probes)
        self.inside_cache[key] = valid
        return valid

    def _in_antenna_keepout(self, ix: int, iy: int) -> bool:
        x = ix * GRID_MM
        y = iy * GRID_MM
        left, top, right, bottom = self.antenna_rect
        return left <= x <= right and top <= y <= bottom

    def _build_static_obstacles(self) -> None:
        pad_margin = CLEARANCE_MM + SIGNAL_WIDTH_MM / 2
        for footprint in all_footprints(self.board):
            for pad in all_pads(footprint):
                layers = pad_layers(pad)
                if not layers:
                    continue
                bbox = pad.GetBoundingBox()
                left = pcbnew.ToMM(bbox.GetLeft()) - pad_margin
                top = pcbnew.ToMM(bbox.GetTop()) - pad_margin
                right = pcbnew.ToMM(bbox.GetRight()) + pad_margin
                bottom = pcbnew.ToMM(bbox.GetBottom()) + pad_margin
                net_name = pad.GetNetname() or "__NO_NET__"
                for ix, iy in iter_grid_box(left, top, right, bottom):
                    x = ix * GRID_MM
                    y = iy * GRID_MM
                    if left <= x <= right and top <= y <= bottom:
                        for layer in layers:
                            self.pad_blocked[layer][(ix, iy)].add(net_name)

                via_margin = VIA_DIAMETER_MM / 2 + CLEARANCE_MM
                for ix, iy in iter_grid_box(
                    left - via_margin,
                    top - via_margin,
                    right + via_margin,
                    bottom + via_margin,
                ):
                    self.via_forbidden.add((ix, iy))

            courtyard_layer = (
                pcbnew.B_CrtYd if footprint.IsFlipped() else pcbnew.F_CrtYd
            )
            courtyard = footprint.GetCourtyard(courtyard_layer)
            if (
                footprint.GetReference() != "J1"
                and courtyard.OutlineCount()
                and not courtyard.IsEmpty()
            ):
                bbox = courtyard.BBox()
                margin = VIA_DIAMETER_MM / 2 + 0.15
                left = pcbnew.ToMM(bbox.GetLeft()) - margin
                top = pcbnew.ToMM(bbox.GetTop()) - margin
                right = pcbnew.ToMM(bbox.GetRight()) + margin
                bottom = pcbnew.ToMM(bbox.GetBottom()) + margin
                for ix, iy in iter_grid_box(left, top, right, bottom):
                    self.via_forbidden.add((ix, iy))

    def _build_terminal_escapes(self) -> None:
        for footprint in all_footprints(self.board):
            for pad in all_pads(footprint):
                net_name = pad.GetNetname()
                if not net_name or not pad_layers(pad):
                    continue
                terminal = terminal_for_pad(pad)
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        if abs(dx) + abs(dy) <= 4:
                            self.terminal_escape[net_name].add(
                                (
                                    terminal[0] + dx,
                                    terminal[1] + dy,
                                    terminal[2],
                                )
                            )

    def _seed_existing_routing(self) -> None:
        existing = list(self.board.GetTracks())
        KEEPALIVE.extend(existing)
        for item in existing:
            net_name = item.GetNetname()
            if not net_name:
                continue
            if isinstance(item, pcbnew.PCB_VIA):
                width = pcbnew.ToMM(item.GetWidth(pcbnew.F_Cu))
                x, y = pos_mm(item)
                nodes = [
                    grid_node(x, y, F_LAYER),
                    grid_node(x, y, B_LAYER),
                ]
                self._reserve(nodes, net_name, max(width, VIA_DIAMETER_MM))
                continue
            width = pcbnew.ToMM(item.GetWidth())
            sx = pcbnew.ToMM(item.GetStart().x)
            sy = pcbnew.ToMM(item.GetStart().y)
            ex = pcbnew.ToMM(item.GetEnd().x)
            ey = pcbnew.ToMM(item.GetEnd().y)
            distance = math.hypot(ex - sx, ey - sy)
            count = max(1, math.ceil(distance / GRID_MM))
            layer = F_LAYER if item.GetLayer() == pcbnew.F_Cu else B_LAYER
            sampled = [
                grid_node(
                    sx + (ex - sx) * index / count,
                    sy + (ey - sy) * index / count,
                    layer,
                )
                for index in range(count + 1)
            ]
            self._reserve(sampled, net_name, width)

    def _valid(self, node: Node, net_name: str) -> bool:
        ix, iy, layer = node
        if not self._inside(ix, iy) or self._in_antenna_keepout(ix, iy):
            return False
        if node not in self.terminal_escape[net_name]:
            pad_nets = self.pad_blocked[layer].get((ix, iy), set())
            if any(name != net_name for name in pad_nets):
                return False
        occupant = self.occupied[layer].get((ix, iy))
        return occupant is None or occupant == net_name

    def _neighbors(self, node: Node, net_name: str):
        ix, iy, layer = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidate = (ix + dx, iy + dy, layer)
            if self._valid(candidate, net_name):
                yield candidate, 1.0
        other = B_LAYER if layer == F_LAYER else F_LAYER
        candidate = (ix, iy, other)
        if (
            (
                (ix, iy) not in self.via_forbidden
                or node in self.terminal_escape[net_name]
            )
            and self._valid(candidate, net_name)
        ):
            yield candidate, 12.0

    @staticmethod
    def _heuristic(node: Node, target: Node) -> float:
        layer_cost = 0 if node[2] == target[2] else 8
        return abs(node[0] - target[0]) + abs(node[1] - target[1]) + layer_cost

    def _route_to_tree(
        self,
        net_name: str,
        tree: set[Node],
        target: Node,
    ) -> list[Node]:
        queue: list[tuple[float, float, Node]] = []
        cost: dict[Node, float] = {}
        parent: dict[Node, Node | None] = {}
        for start in tree:
            cost[start] = 0.0
            parent[start] = None
            heappush(
                queue,
                (self._heuristic(start, target), 0.0, start),
            )

        while queue:
            _, current_cost, current = heappop(queue)
            if current_cost != cost.get(current):
                continue
            if current == target:
                path: list[Node] = []
                cursor: Node | None = current
                while cursor is not None:
                    path.append(cursor)
                    cursor = parent[cursor]
                path.reverse()
                return path
            for neighbor, step_cost in self._neighbors(current, net_name):
                next_cost = current_cost + step_cost
                if next_cost >= cost.get(neighbor, math.inf):
                    continue
                cost[neighbor] = next_cost
                parent[neighbor] = current
                heappush(
                    queue,
                    (
                        next_cost + self._heuristic(neighbor, target),
                        next_cost,
                        neighbor,
                    ),
                )
        raise RuntimeError(f"Could not route {net_name} to {target}")

    def _reserve(self, path: list[Node], net_name: str, width: float) -> None:
        minimum_center_spacing = (
            width / 2 + CLEARANCE_MM + SIGNAL_WIDTH_MM / 2
        )
        radius = max(1, math.ceil(minimum_center_spacing / GRID_MM))
        for ix, iy, layer in path:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if (
                        math.hypot(dx, dy) * GRID_MM
                        < minimum_center_spacing - 0.001
                    ):
                        key = (ix + dx, iy + dy)
                        existing = self.occupied[layer].get(key)
                        if existing is None or existing == net_name:
                            self.occupied[layer][key] = net_name
            self.net_nodes[net_name].add((ix, iy, layer))

    @staticmethod
    def _simplify(path: list[Node]) -> list[Node]:
        if len(path) < 3:
            return path
        result = [path[0]]
        for index in range(1, len(path) - 1):
            previous = result[-1]
            current = path[index]
            following = path[index + 1]
            if previous[2] != current[2] or current[2] != following[2]:
                result.append(current)
                continue
            first_direction = (
                current[0] - previous[0],
                current[1] - previous[1],
            )
            second_direction = (
                following[0] - current[0],
                following[1] - current[1],
            )
            if (
                first_direction[0] * second_direction[1]
                != first_direction[1] * second_direction[0]
            ):
                result.append(current)
        result.append(path[-1])
        return result

    def _emit(
        self,
        path: list[Node],
        net: pcbnew.NETINFO_ITEM,
        width: float,
    ) -> None:
        for start, end in zip(
            self._simplify(path),
            self._simplify(path)[1:],
        ):
            if start[2] == end[2]:
                track = pcbnew.PCB_TRACK(self.board)
                track.SetStart(point(*node_xy(start)))
                track.SetEnd(point(*node_xy(end)))
                track.SetLayer(LAYER_ID[start[2]])
                track.SetWidth(mm(width))
                track.SetNet(net)
                self.board.Add(track)
            else:
                if start[:2] != end[:2]:
                    raise RuntimeError("Layer change moved XY coordinate")
                via = pcbnew.PCB_VIA(self.board)
                via.SetPosition(point(*node_xy(start)))
                via.SetWidth(mm(VIA_DIAMETER_MM))
                via.SetDrill(mm(VIA_DRILL_MM))
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetNet(net)
                self.board.Add(via)

    def _connect_pad_to_grid(
        self,
        pad: pcbnew.PAD,
        node: Node,
        net: pcbnew.NETINFO_ITEM,
        width: float,
    ) -> None:
        px, py = pos_mm(pad)
        gx, gy = node_xy(node)
        if math.hypot(px - gx, py - gy) < 0.005:
            return
        track = pcbnew.PCB_TRACK(self.board)
        track.SetStart(point(px, py))
        track.SetEnd(point(gx, gy))
        track.SetLayer(LAYER_ID[node[2]])
        track.SetWidth(mm(width))
        track.SetNet(net)
        self.board.Add(track)

    def route_net(
        self,
        net: pcbnew.NETINFO_ITEM,
        terminals: list[pcbnew.PAD],
        width: float,
    ) -> None:
        net_name = net.GetNetname()
        unique: dict[Node, pcbnew.PAD] = {}
        for pad in terminals:
            node = terminal_for_pad(pad)
            unique.setdefault(node, pad)
        if len(unique) < 2:
            return

        root = next(
            (
                node
                for node, pad in unique.items()
                if pad.GetParentFootprint().GetReference() == "U1"
            ),
            next(iter(unique)),
        )
        tree: set[Node] = {root}
        self._reserve([root], net_name, width)
        remaining = set(unique) - {root}
        emitted_paths: list[list[Node]] = []

        while remaining:
            target = min(
                remaining,
                key=lambda item: min(
                    abs(item[0] - tree_node[0])
                    + abs(item[1] - tree_node[1])
                    + (8 if item[2] != tree_node[2] else 0)
                    for tree_node in tree
                ),
            )
            path = self._route_to_tree(net_name, tree, target)
            emitted_paths.append(path)
            tree.update(path)
            self._reserve(path, net_name, width)
            remaining.remove(target)

        for path in emitted_paths:
            self._emit(path, net, width)
        for node, pad in unique.items():
            self._connect_pad_to_grid(pad, node, net, width)


def route_board(
    board: pcbnew.BOARD,
    nets: dict[str, pcbnew.NETINFO_ITEM],
) -> None:
    by_net: dict[str, list[pcbnew.PAD]] = defaultdict(list)
    for footprint in all_footprints(board):
        for pad in all_pads(footprint):
            if pad.GetNetname():
                by_net[pad.GetNetname()].append(pad)

    route_usb_pair_manually(board, nets)
    route_led_anodes_manually(board, nets, footprint_map(board))
    router = GridRouter(board)
    order = [
        "STATUS_LED_5_MCU",
        "STATUS_LED_4_MCU",
        "STATUS_LED_3_MCU",
        "STATUS_LED_2_MCU",
        "STATUS_LED_1_MCU",
        "VBUS",
        "3V3",
        "BUZZER_SW",
        "BUZZER_GPIO",
        "BUZZER_GATE",
        "EN",
        "BOOT_GPIO0",
        "OLED_SDA",
        "OLED_SCL",
        "UART_TX_MCU",
        "UART_RX_MCU",
        "PLAYER_UART_TX",
        "PLAYER_UART_RX",
        "CHAL_0_MCU",
        "CHAL_1_MCU",
        "CHAL_2_MCU",
        "CHAL_0",
        "CHAL_1",
        "CHAL_2",
        "GAME_LEFT",
        "GAME_OK",
        "GAME_RIGHT",
        "USB_CC1",
        "USB_CC2",
    ]
    widths = defaultdict(lambda: SIGNAL_WIDTH_MM)
    widths["3V3"] = POWER_WIDTH_MM
    widths["VBUS"] = VBUS_WIDTH_MM
    widths["BUZZER_SW"] = 0.5

    for net_name in order:
        print(f"Routing {net_name} ({len(by_net[net_name])} pads)")
        router.route_net(nets[net_name], by_net[net_name], widths[net_name])


def rectangle_poly(
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


def add_antenna_rule_area(board: pcbnew.BOARD) -> None:
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
    keepout.SetOutline(rectangle_poly(95.4, 59.7, 104.0, 82.3))
    board.Add(keepout)


def add_ground_zones(
    board: pcbnew.BOARD,
    gnd: pcbnew.NETINFO_ITEM,
) -> None:
    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline, False):
        raise RuntimeError("Cannot build ground plane from board outline")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        print(f"  Creating GND zone on layer {layer}", flush=True)
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(gnd)
        zone.SetLocalClearance(mm(0.25))
        zone.SetMinThickness(mm(0.2))
        zone.SetThermalReliefGap(mm(0.3))
        zone.SetThermalReliefSpokeWidth(mm(0.35))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetOutline(outline.CloneDropTriangulation())
        board.Add(zone)

    # KiCad 10's standalone macOS Python binding crashes in ZONE_FILLER
    # without a GUI wx.App. The board is saved with valid zone outlines and
    # KiCad CLI performs the fill before DRC and manufacturing export.


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    remove_routing_and_zones(board)
    replace_power_and_add_buzzer(board)
    parts = footprint_map(board)
    nets = assign_board_nets(board, parts)
    route_board(board, nets)
    print("Saving board", flush=True)
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Saved production PCB: {BOARD_PATH}")


if __name__ == "__main__":
    main()
