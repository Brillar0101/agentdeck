"""Export V2 board positions for the enclosure scripts (Phase 4).

Run with KiCad's bundled python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/\
Current/bin/python3 v2/tools/export_positions_v2.py \
      --pcb v2/hardware/AgentDeckV2.kicad_pcb \
      --out v2/enclosure/positions.json

Writes key centers, mounting holes, control parts (with courtyard bboxes),
the OLED glass rectangle (largest F.Fab rect of OLED1) and the battery
pocket rectangle drawn on User.Drawings. All values are board mm, y-down.
"""
import argparse
import json

import pcbnew

CTRL_REFS = ("ENC1", "OLED1", "TP1", "J1", "J2", "SW25", "SW26", "SW27", "U1")


def mm(nm: int) -> float:
    return round(nm / 1e6, 3)


def courtyard_bbox(fp):
    shape = fp.GetCourtyard(pcbnew.F_CrtYd)
    if shape.OutlineCount() == 0:
        bb = fp.GetBoundingBox(False)
    else:
        bb = shape.BBox()
    return [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]


def fab_glass_rect(fp):
    """Largest F.Fab rectangle of a footprint, board coords (OLED glass)."""
    best, best_area = None, 0.0
    for item in fp.GraphicalItems():
        if not isinstance(item, pcbnew.PCB_SHAPE):
            continue
        if item.GetLayer() != pcbnew.F_Fab or item.GetShape() != pcbnew.SHAPE_T_RECT:
            continue
        bb = item.GetBoundingBox()
        area = bb.GetWidth() * bb.GetHeight()
        if area > best_area:
            best_area = area
            best = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
    return best


def battery_rect(board):
    """Rect drawn on User.Drawings marking the battery pocket."""
    best, best_area = None, 0.0
    for d in board.GetDrawings():
        if not isinstance(d, pcbnew.PCB_SHAPE):
            continue
        if d.GetLayer() != pcbnew.Dwgs_User or d.GetShape() != pcbnew.SHAPE_T_RECT:
            continue
        bb = d.GetBoundingBox()
        area = bb.GetWidth() * bb.GetHeight()
        if area > best_area:
            best_area = area
            best = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
    if best is None:
        raise SystemExit("no battery rect found on User.Drawings")
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcb", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.pcb)
    bb = board.GetBoardEdgesBoundingBox()
    edge_w = 0.1  # Edge.Cuts line width; the bbox includes half of it per side
    out = {
        "board": {
            "x0": round(mm(bb.GetLeft()) + edge_w / 2, 2),
            "y0": round(mm(bb.GetTop()) + edge_w / 2, 2),
            "x1": round(mm(bb.GetRight()) - edge_w / 2, 2),
            "y1": round(mm(bb.GetBottom()) - edge_w / 2, 2),
            "corner_r": 6.0,
            "thickness": 1.6,
        },
        "holes": {},
        "keys": {},
        "ctrl": {},
        "battery": battery_rect(board),
        "usb": {"top": True},
    }
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        p = fp.GetPosition()
        if ref.startswith("MH"):
            out["holes"][ref] = [mm(p.x), mm(p.y)]
        elif ref.startswith("SW") and ref not in ("SW25", "SW26", "SW27") \
                and "Choc" in str(fp.GetFPID().GetLibItemName()):
            out["keys"][ref] = [mm(p.x), mm(p.y)]
        if ref in CTRL_REFS:
            entry = {
                "pos": [mm(p.x), mm(p.y)],
                "rot": fp.GetOrientationDegrees(),
                "bbox": courtyard_bbox(fp),
            }
            if ref == "OLED1":
                entry["glass"] = fab_glass_rect(fp)
            out["ctrl"][ref] = entry
    if len(out["keys"]) != 24:
        raise SystemExit(f"expected 24 keys, found {len(out['keys'])}")
    if len(out["holes"]) != 6:
        raise SystemExit(f"expected 6 mounting holes, found {len(out['holes'])}")
    out["usb"]["x"] = out["ctrl"]["J1"]["pos"][0]
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(f"wrote {args.out}: {len(out['keys'])} keys, {len(out['holes'])} holes, "
          f"battery {out['battery']}, usb x={out['usb']['x']}")


if __name__ == "__main__":
    main()
