#!/usr/bin/env python3
"""Apply final pad and silkscreen overrides to the routed production board."""

from pathlib import Path
import os

import pcbnew


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
HIDE_REFERENCES = {
    "BZ1",
    "Q_BZ",
    "D_BZ",
    "R_BZ",
    "R_BZ_PD",
    "C9",
    "U2",
}


def main() -> None:
    board = pcbnew.LoadBoard(str(BOARD_PATH))
    keepalive: list[object] = []

    for footprint in board.GetFootprints():
        keepalive.append(footprint)
        if footprint.GetReference() in HIDE_REFERENCES:
            footprint.Reference().SetVisible(False)
            footprint.Value().SetVisible(False)
        if footprint.GetReference() == "J1":
            models = footprint.Models()
            keepalive.append(models)
            if models:
                models[0].m_Filename = (
                    "${KICAD10_3DMODEL_DIR}/Connector_USB.3dshapes/"
                    "USB_C_Receptacle_GCT_USB4105-xx-A_16P_"
                    "TopMnt_Horizontal.step"
                )
            for pad in footprint.Pads():
                keepalive.append(pad)
                if pad.GetNumber() in {"A1", "B12", "SH"}:
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    keepalive.extend(board.Zones())
    pcbnew.SaveBoard(str(BOARD_PATH), board)
    print(f"Applied production overrides: {BOARD_PATH}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
