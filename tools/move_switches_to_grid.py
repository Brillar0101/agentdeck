"""Place every switch centre (pole + keycap), the encoder, and the joystick on
one uniform 18x18mm grid at 18/36/54/72 in both axes.

With 17.5mm caps this yields a consistent 0.5mm gap between every neighbouring
cap and an identical 9.25mm margin to all four board edges (90x90 outline), and
keeps every control on shared row/column lines.

Ground truth (measured): the hotswap sockets sit on B.Cu and their switch
centre = footprint origin + (+2.5, -4.8) in board space, uniformly (rot 0), so
each socket origin is placed at target centre + (-2.5, +4.8). The mechanical
hole pattern (pole + legs + electrical PTH) moves rigidly with the footprint
and is left untouched. Routing + padless carriers are stripped for a clean
re-route; the finish pipeline rebuilds carriers and mounting holes.
"""
import re

F = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
SWITCH_LIB = "CONN-SMD_HOTPLUGPAKAGE__C9900010116"
CENTER_DX, CENTER_DY = 2.5, -4.8   # switch centre = socket origin + this

# target switch-centre / control positions on the uniform 18mm grid
TARGETS = {
    "ENC1": (18, 18), "SW1": (36, 18), "SW2": (54, 18), "JS1": (72, 18),
    "SW3": (18, 36), "SW4": (36, 36), "SW5": (54, 36), "SW6": (72, 36),
    "SW7": (18, 54), "SW8": (36, 54), "SW9": (54, 54), "SW10": (72, 54),
    "SW11": (45, 72), "SW12": (72, 72),
}


def match_block(s, i):
    depth = 0
    while i < len(s):
        if s[i] == '"':
            i += 1
            while i < len(s) and s[i] != '"':
                if s[i] == '\\':
                    i += 1
                i += 1
        elif s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced")


def footprint_ref(block):
    m = re.search(r'\(property "Reference" "([^"]+)"', block)
    return m.group(1) if m else ""


def set_origin(block, ax, ay):
    """Rewrite the footprint-level (at x y[ rot]) that precedes the first property."""
    p = block.find('(property')
    head, tail = block[:p], block[p:]
    head = re.sub(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)([^\)]*)\)',
                  lambda m: f'(at {round(ax, 4):g} {round(ay, 4):g}{m.group(3)})',
                  head, count=1)
    return head + tail


txt = open(F).read()
root_open = txt.find('(kicad_pcb')
body_start = txt.find('(', root_open + 1)
end_of_root = match_block(txt, root_open) - 1
out = [txt[:body_start]]
i = body_start
dropped = {"segment": 0, "via": 0, "zone": 0, "carrier": 0}
moved_sw = moved_ctrl = 0

while i < end_of_root:
    if txt[i] in ' \t\n' or txt[i] != '(':
        out.append(txt[i])
        i += 1
        continue
    end = match_block(txt, i)
    block = txt[i:end]
    tok = block[1:].split(None, 1)[0].strip('()')
    if tok in ("segment", "via", "zone"):
        dropped[tok] += 1
        i = end
        continue
    if tok == "footprint":
        ref = footprint_ref(block)
        if SWITCH_LIB in block and ref in TARGETS:
            cx, cy = TARGETS[ref]
            block = set_origin(block, cx - CENTER_DX, cy - CENTER_DY)
            moved_sw += 1
        elif ref in ("ENC1", "JS1"):
            cx, cy = TARGETS[ref]
            block = set_origin(block, cx, cy)
            moved_ctrl += 1
        elif ref.startswith("KEY") or ref.startswith("MH"):
            dropped["carrier"] += 1
            i = end
            continue
    out.append(block)
    i = end

out.append(txt[end_of_root:])
open(F, "w").write(''.join(out))
print(f"sockets moved: {moved_sw}, controls moved: {moved_ctrl}, dropped: {dropped}")
