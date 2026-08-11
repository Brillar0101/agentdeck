#!/usr/bin/env python3
"""Set the silkscreen text face to Red Hat Mono.

pcbnew exposes EDA_TEXT::SetFont but not the KIFONT_FONT binding needed to
build a font object, so the face is injected straight into the board file:
every gr_text / fp_text block whose layer is a Silkscreen layer gets a
(face "Red Hat Mono") entry inside its (font ...) block.

Note this departs from the usual stroke-font guidance - Red Hat Mono is an
outline font and KiCad renders it as filled polygons in the gerbers. It is
legible at the 1.0 mm height silk_pass.py enforces, but counters (the holes in
e, a, 8, R) tighten as text approaches the 0.8 mm floor.

Plain text rewrite - no pcbnew, so it runs under any python3.
Run:  python3 tools/fix_silk_font.py <board.kicad_pcb> [face]
"""
import os
import re
import sys

BOARD = sys.argv[1] if len(sys.argv) > 1 else None
FACE = sys.argv[2] if len(sys.argv) > 2 else "Red Hat Mono"
if not BOARD or not os.path.exists(BOARD):
    raise SystemExit("usage: fix_silk_font.py <board.kicad_pcb> [face]")

src = open(BOARD).read()


def blocks(text, opener):
    """Yield (start, end) spans of every s-expression starting with opener."""
    out = []
    for m in re.finditer(r"\(" + opener + r"\b", text):
        i = m.start()
        depth = 0
        j = i
        in_str = False
        while j < len(text):
            ch = text[j]
            if in_str:
                if ch == "\\":
                    j += 2
                    continue
                if ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    out.append((i, j + 1))
                    break
            j += 1
    return out


edits = []
for opener in ("gr_text", "fp_text", "property"):
    for (i, j) in blocks(src, opener):
        chunk = src[i:j]
        # the file stores the canonical layer name "F.SilkS" - "F.Silkscreen"
        # is only the user-facing alias in the layer table at the top
        if '"F.SilkS"' not in chunk and '"B.SilkS"' not in chunk:
            continue
        fonts = blocks(chunk, "font")
        if not fonts:
            continue
        fi, fj = fonts[0]
        if "(face" in chunk[fi:fj]:
            continue
        ins = i + fi + len("(font")
        # Bold, deliberately: Red Hat Mono Regular stems at 1.0 mm are thinner
        # than the 0.15 mm fab minimum and KiCad flags them as "insufficient
        # stroke weight". The bold face clears it without growing the text.
        bold = "(bold yes)" not in chunk[fi:fj]
        edits.append((ins, bold))

for (ins, bold) in sorted(edits, reverse=True):
    add = f'\n\t\t\t\t(face "{FACE}")'
    if bold:
        add += "\n\t\t\t\t(bold yes)"
    src = src[:ins] + add + src[ins:]

open(BOARD, "w").write(src)
print(f"set face {FACE!r} on {len(edits)} silkscreen text block(s)")
