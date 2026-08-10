#!/usr/bin/env python3
from pathlib import Path
import os

import pcbnew
import wx


ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "hacking_box_v2.kicad_pcb"

app = wx.App(False)
board = pcbnew.LoadBoard(str(BOARD_PATH))
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(str(BOARD_PATH), board)
os._exit(0)
