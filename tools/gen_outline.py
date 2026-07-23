#!/usr/bin/env python3
"""Generate board_outline.kicad_pcb: 90x90mm rounded square (r=6mm),
1.6mm stackup (SKQUCAA010 snap-in datasheet requirement).

Run with KiCad's bundled python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 tools/gen_outline.py
"""
import os
import pcbnew

W = H = 90.0
R = 6.0
OUT = os.path.join(os.path.dirname(__file__), "..", "board_outline.kicad_pcb")

board = pcbnew.CreateEmptyBoard()
MM = pcbnew.FromMM


def line(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    board.Add(s)


def arc(cx, cy, sx, sy, angle_deg):
    a = pcbnew.PCB_SHAPE(board)
    a.SetShape(pcbnew.SHAPE_T_ARC)
    a.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
    a.SetStart(pcbnew.VECTOR2I(MM(sx), MM(sy)))
    a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T), False)
    a.SetLayer(pcbnew.Edge_Cuts)
    a.SetWidth(MM(0.1))
    board.Add(a)


line(R, 0, W - R, 0)
arc(W - R, R, W - R, 0, 90)
line(W, R, W, H - R)
arc(W - R, H - R, W, H - R, 90)
line(W - R, H, R, H)
arc(R, H - R, R, H, 90)
line(0, H - R, 0, R)
arc(R, R, 0, R, 90)

ds = board.GetDesignSettings()
ds.SetBoardThickness(MM(1.6))
pcbnew.SaveBoard(OUT, board)
print("wrote", os.path.normpath(OUT))
