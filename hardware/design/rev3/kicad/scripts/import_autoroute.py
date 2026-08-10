#!/usr/bin/env python3
"""Import a FreeRouting Specctra session into the production board."""

from pathlib import Path
import os
import shutil

import pcbnew
import wx


ROOT = Path(__file__).resolve().parents[1]
AUTOROUTE_DIR = (
    ROOT.parents[3]
    / "archive"
    / "design"
    / "rev3-development"
    / "autoroute"
)
UNROUTED_BOARD = AUTOROUTE_DIR / "hacking_box_v3_unrouted.kicad_pcb"
SESSION_PATH = AUTOROUTE_DIR / "hacking_box_v3.ses"
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"
PREIMPORT_BACKUP = AUTOROUTE_DIR / "hacking_box_v2_preimport.kicad_pcb"


def main() -> None:
    app = wx.App(False)
    if not UNROUTED_BOARD.exists():
        raise FileNotFoundError(UNROUTED_BOARD)
    if not SESSION_PATH.exists():
        raise FileNotFoundError(SESSION_PATH)

    shutil.copy2(BOARD_PATH, PREIMPORT_BACKUP)
    board = pcbnew.LoadBoard(str(UNROUTED_BOARD))
    if not pcbnew.ImportSpecctraSES(board, str(SESSION_PATH)):
        raise RuntimeError(f"Specctra session import failed: {SESSION_PATH}")
    pcbnew.SaveBoard(str(BOARD_PATH), board)

    print(f"Saved pre-import backup: {PREIMPORT_BACKUP}")
    print(f"Imported routed board: {BOARD_PATH}")
    os._exit(0)


if __name__ == "__main__":
    main()
