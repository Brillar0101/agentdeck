"""Deterministic s-expression fix for ClaudeMicro.kicad_pcb (bypasses the
unstable pcbnew SWIG proxies in this environment).

1. Every Choc hotswap footprint (CONN-SMD_HOTPLUGPAKAGE__C9900010116) gets its
   mechanical NPTH holes recentred on the switch centre = footprint origin:
     - central pole  Ø3.4 at (0, 0)   (Choc V1 PG1350 locating-pole fit)
     - two legs      Ø1.7 at (-5.5, 0) and (+5.5, 0)
   The 2 electrical PTH holes (Ø3) and 2 SMD pads are left untouched -> 5 holes.
2. ENC1 + JS1 move up to y=15 (kept aligned to each other), clearing the top key
   row / their 3D knobs.
3. Copper routing (segments, vias, zones) and the KEY*/MH* carrier footprints are
   stripped so the board can be re-routed cleanly; the finish pipeline rebuilds
   carriers + mounting holes afterwards.
"""
import re
import uuid

F = "/Users/barakaeli/kicad-projects/claude-micro/ClaudeMicro.kicad_pcb"
SWITCH_LIB = "CONN-SMD_HOTPLUGPAKAGE__C9900010116"
CTRL_Y = 15.0

# mis-offset mechanical NPTH holes to drop (local coords, same in every switch)
DROP = {(-3.0, -4.8), (2.5, -4.8), (7.5, -9.95), (8.0, -4.8)}


def match_block(s, i):
    """Given s[i] == '(', return index just past the matching ')'."""
    depth = 0
    while i < len(s):
        if s[i] == '"':                       # skip strings
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


def new_pad(x, y, d):
    return (
        '\t\t(pad "" np_thru_hole circle\n'
        f'\t\t\t(at {x} {y})\n'
        f'\t\t\t(size {d} {d})\n'
        f'\t\t\t(drill {d})\n'
        '\t\t\t(layers "*.Cu" "*.Mask")\n'
        f'\t\t\t(uuid "{uuid.uuid4()}")\n'
        '\t\t)\n'
    )


def fix_switch(block):
    """Drop mis-offset NPTH pads, inject 3 recentred holes before the final ')'."""
    out, i = [], 0
    while i < len(block):
        if block.startswith('(pad ', i):
            end = match_block(block, i)
            pad = block[i:end]
            keep = True
            if 'np_thru_hole' in pad:
                m = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)', pad)
                if m and (round(float(m.group(1)), 2), round(float(m.group(2)), 2)) in DROP:
                    keep = False
            if keep:
                out.append(pad)
            i = end
        else:
            out.append(block[i])
            i += 1
    rebuilt = ''.join(out)
    inject = new_pad(0, 0, 3.4) + new_pad(-5.5, 0, 1.7) + new_pad(5.5, 0, 1.7)
    close = rebuilt.rfind(')')
    return rebuilt[:close] + inject + rebuilt[close:]


def footprint_ref(block):
    m = re.search(r'\(property "Reference" "([^"]+)"', block)
    return m.group(1) if m else ""


def move_ctrl(block):
    """Set the footprint-level (at x y[ rot]) y to CTRL_Y (before first property)."""
    p = block.find('(property')
    head = block[:p]
    head = re.sub(r'(\(at\s+-?[\d.]+\s+)-?[\d.]+',
                  lambda m: f'{m.group(1)}{CTRL_Y}', head, count=1)
    return head + block[p:]


txt = open(F).read()

# walk top-level children of (kicad_pcb ...)
root_open = txt.find('(kicad_pcb')
body_start = txt.find('(', root_open + 1)
out = [txt[:body_start]]
i = body_start
dropped = {"segment": 0, "via": 0, "zone": 0, "carrier": 0}
switches = ctrls = 0
end_of_root = match_block(txt, root_open) - 1     # index of root's final ')'

while i < end_of_root:
    if txt[i] in ' \t\n':
        out.append(txt[i])
        i += 1
        continue
    if txt[i] != '(':
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
        if SWITCH_LIB in block and ref.startswith("SW"):
            block = fix_switch(block)
            switches += 1
        elif ref in ("ENC1", "JS1"):
            block = move_ctrl(block)
            ctrls += 1
        elif ref.startswith("KEY") or ref.startswith("MH"):
            dropped["carrier"] += 1
            i = end
            continue
    out.append(block)
    i = end

out.append(txt[end_of_root:])
open(F, "w").write(''.join(out))
print(f"switches recentred: {switches}, controls moved: {ctrls}, dropped: {dropped}")
