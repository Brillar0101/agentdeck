"""Open the U1 routing corridor, fix J1 clearance override, relocate colliding silk texts."""
import pcbnew

BOARD = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
board = pcbnew.LoadBoard(BOARD)
mm = pcbnew.FromMM


def to_mm(v):
    return pcbnew.ToMM(v)


# Phase 1: gather everything (no mutation before all reads — SWIG dispatch breaks otherwise)
fps = {}
bboxes = []
for fp in board.GetFootprints():
    fps[fp.GetReference()] = fp
    bb = fp.GetBoundingBox(False)
    bboxes.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))

texts = []
for d in board.GetDrawings():
    if isinstance(d, pcbnew.PCB_TEXT):
        texts.append(d)

# Phase 2: mutate
# 1. open the corridor: C10 west, C11 east (staying decoupling-close to U1)
fps["C10"].SetPosition(pcbnew.VECTOR2I(mm(38.0), mm(88.4)))
fps["C11"].SetPosition(pcbnew.VECTOR2I(mm(50.7), mm(88.4)))
print("C10 -> (38.0, 88.4), C11 -> (50.7, 88.4)")

# 2. J1 USB-C local clearance override (factory pad geometry is 0.10mm)
fps["J1"].SetLocalClearance(mm(0.09))
print("J1 local clearance override 0.09mm")


# 3. relocate colliding silk texts to verified-free spots
def spot_is_free(x0, y0, x1, y1, margin):
    m = mm(margin)
    for bx0, by0, bx1, by1 in bboxes:
        if x0 - m < bx1 and x1 + m > bx0 and y0 - m < by1 and y1 + m > by0:
            return False
    return True


def relocate(txt, candidates):
    label = txt.GetText()[:30]
    for x, y, rot in candidates:
        txt.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        txt.SetTextAngleDegrees(rot)
        bb = txt.GetBoundingBox()
        if spot_is_free(bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom(), 0.3) \
                and bb.GetLeft() > mm(1.5) and bb.GetRight() < mm(88.5) \
                and bb.GetTop() > mm(1.5) and bb.GetBottom() < mm(88.5):
            print(f"'{label}' -> ({x}, {y}) rot {rot}")
            return True
    print(f"WARNING: no free spot found for '{label}'")
    return False


CANDIDATES = [
    (45.0, 78.2, 0), (45.0, 66.4, 0), (45.0, 61.5, 0), (45.0, 49.0, 0),
    (45.0, 31.5, 0), (25.0, 78.2, 0), (65.0, 78.2, 0), (45.0, 12.5, 0),
    (86.5, 45.0, 90), (3.5, 45.0, 90), (45.0, 86.9, 0),
]
for t in texts:
    s = t.GetText()
    if "OSHW" in s or "FLASH" in s:
        used = relocate(t, CANDIDATES)
        if used:
            bb = t.GetBoundingBox()
            bboxes.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))

pcbnew.SaveBoard(BOARD, board)
print("board saved")
