"""AgentDeck V2 two-part case with brass heat-set inserts + cover plugs.

Ported from tools/make_case.py (V1). Same fastener system, V2 geometry.
Stack-up, z=0 is the PCB underside. The lid is deliberately LOW - the
keycaps and knob float above it.

     5.5 ---- top of lid ------------------------------
             cover plug  O4.8 x 1.4, sits on the screw head
     4.0 ---------------------------------------------
             M2.5 countersunk head (ISO 7046) O5.0, 90 deg
     2.95 --- countersink begins (1.35 mm of lid under head)
             screw shank, clearance O2.9
     1.6 ---- lid underside rests on PCB top ----------
             PCB 1.6 mm, mounting hole O2.7
     0.0 ---- PCB underside rests on boss -------------
             boss O8.0, insert pocket O3.6 x 5.5 deep
             brass heat-set insert  M2.5 x L4.0 x OD4.0
    -4.0 ---- cavity floor (4.0 mm clears bottom parts: SK6812 drop-through
             bodies ~0.2 below board + THT tails)
    -8.5 ---- battery pocket floor (42x32 recess, LiPo 803040 8.0 + margin)
   -10.9 ---- bottom of case (floor 2.4 mm under the pocket)

Fasteners (identical to V1, verified against supplier data):
  * Brass heat-set insert  M2.5 x 0.45, OD 4.0 mm, length 4.0 mm
      boss pilot hole 3.6 mm, +1.5 mm relief for displaced plastic / screw tip
  * Screw  M2.5 x 8 mm countersunk, engagement 1.5 lid + 1.6 PCB + 4.0 insert

V2 lid additions over the V1 plate lid:
  * global 2.6 mm underside relief (1.3 mm skin) clears all low SMD parts
  * deeper pocket over the ESP32-S3 module (ceiling skin 0.5 mm) + open
    antenna slot through the top-edge band (module overhangs the board edge)
  * OLED through-window (glass + 0.6) with a 1.0 mm recessed ledge on top so
    a cover glass sits flush with the lid surface
  * touch zone kept SOLID, thinned to 1.0 mm, finger-guide ring engraved on top
  * J2 battery-connector access hatch (housing is 6.0 mm - taller than the lid)
  * BOOT/RESET pen-press holes, USB notch, power-switch side notch
"""
import argparse
import json
import math
import re
import sys

import bmesh
import bpy
from mathutils import Vector

MM = 0.001

# --- hardware (EXACTLY the V1 constants) ---
INS_OD, INS_LEN = 4.0, 4.0          # heat-set insert
PILOT = 3.6                          # boss pilot hole
SCREW_HEAD_D, SCREW_HEAD_H = 5.0, 1.05   # M2.5 countersunk (ISO 7046), 90 deg
CBORE_D = 5.0                            # top of the countersink
SHANK_CLR = 2.9                     # clearance hole through lid
PLUG_D, PLUG_DEPTH = 4.8, 1.4       # thin plug over the flush screw head
BOSS_D = 8.0                        # ~2x insert OD
RELIEF = 1.5                        # insert pocket relief below the insert

# --- case geometry (V1 values; V2 adds the battery-pocket depth) ---
WALL, CLR, CAV, FLOOR = 2.6, 0.5, 4.0, 2.4
LID_BOT, LID_TOP = 1.6, 5.5
CS_START = LID_BOT + 1.35
CS_END = CS_START + SCREW_HEAD_H
PLUG_FLOOR = CS_END
BAT_DEPTH = 8.5                     # pocket floor below PCB underside (8.0 LiPo + 0.5)
BOT_Z = -(BAT_DEPTH + FLOOR)        # exterior bottom

# --- V2 lid reliefs ---
LID_RELIEF_CEIL = 4.2               # global underside relief ceiling (skin 1.3)
U1_CEIL = 5.0                       # ESP32 module pocket ceiling (skin 0.5)
TOUCH_CEIL = 4.5                    # touch zone ceiling -> 1.0 mm solid skin
TOUCH_POCKET_R = 8.0                # underside thinning radius over TP1
GUIDE_R, GUIDE_GROOVE = 6.0, 0.4    # finger-guide ring on the lid top
SW_BODY, FIT = 15.0, 2.4            # Choc body + 1.0 mm clearance per side
OLED_CLR = 0.6                      # window clearance on the glass dims
LEDGE_W, LEDGE_DEPTH = 1.5, 1.0     # cover-glass ledge (glass sits flush)
USB_HALF_W = 7.0                    # USB notch half width
TACT_HOLE_R = 1.75                  # BOOT/RESET pen-press holes


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", required=True)
    ap.add_argument("--parts", required=True, help="v2/PARTS.yaml")
    ap.add_argument("--blend", required=True, help="assembled blend to update")
    ap.add_argument("--outdir", required=True, help="STL output directory")
    return ap.parse_args(argv)


# ---------------- geometry helpers (V1) ----------------
def box(x0, x1, y0, y1, z0, z1):
    bpy.ops.mesh.primitive_cube_add()
    o = bpy.context.active_object
    o.location = ((x0 + x1) / 2 * MM, -(y0 + y1) / 2 * MM, (z0 + z1) / 2 * MM)
    o.scale = ((x1 - x0) / 2 * MM, (y1 - y0) / 2 * MM, (z1 - z0) / 2 * MM)
    bpy.ops.object.transform_apply(scale=True)
    return o


def cyl(x, y, z0, z1, r, v=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r * MM, depth=(z1 - z0) * MM, vertices=v)
    o = bpy.context.active_object
    o.location = (x * MM, -y * MM, (z0 + z1) / 2 * MM)
    return o


def cone(x, y, z0, z1, r_bot, r_top, v=64):
    bpy.ops.mesh.primitive_cone_add(radius1=r_bot * MM, radius2=r_top * MM,
                                    depth=(z1 - z0) * MM, vertices=v)
    o = bpy.context.active_object
    o.location = (x * MM, -y * MM, (z0 + z1) / 2 * MM)
    return o


def torus(x, y, z, major_r, minor_r):
    bpy.ops.mesh.primitive_torus_add(location=(x * MM, -y * MM, z * MM),
                                     major_radius=major_r * MM,
                                     minor_radius=minor_r * MM,
                                     major_segments=64, minor_segments=16)
    return bpy.context.active_object


def bl(t, tool, op):
    m = t.modifiers.new("b", 'BOOLEAN')
    m.operation = op
    m.object = tool
    try:
        m.solver = 'MANIFOLD'   # Blender 4.5+: guarantees watertight output
    except TypeError:
        m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = t
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def rbox(x0, x1, y0, y1, z0, z1, r):
    o = box(x0 + r, x1 - r, y0, y1, z0, z1)
    bl(o, box(x0, x1, y0 + r, y1 - r, z0, z1), 'UNION')
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        bl(o, cyl(cx, cy, z0, z1, r), 'UNION')
    return o


def deisl(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = list(bpy.context.selected_objects)
    main = max(parts, key=lambda p: p.dimensions.x * p.dimensions.y)
    for p in parts:
        if p is not main:
            bpy.data.objects.remove(p, do_unlink=True)
    return main


def nonmanifold_edges(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    n = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    return n


def mesh_cleanup(o):
    """Weld duplicate verts left by boolean seams; keeps geometry intact."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-8)
    bm.to_mesh(o.data)
    bm.free()


def exp(o, path):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              global_scale=1000.0)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True, global_scale=1000.0)


# ---------------- PARTS.yaml (minimal parser, no yaml dep in Blender) -------
def load_parts(path):
    parts, cur = [], None
    for line in open(path):
        m = re.match(r"\s*- ref_prefix:\s*(\S+)", line)
        if m:
            cur = {"ref": m.group(1)}
            parts.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"\s*height_3d:\s*([\d.]+)", line)
        if m:
            cur["h"] = float(m.group(1))
        m = re.match(r"\s*name:\s*(.+?)\s*$", line)
        if m and "name" not in cur:
            cur["name"] = m.group(1)
    return parts


def verify_heights(parts):
    """Assert the lid/case clears every manifest height_3d. Prints a table."""
    modes = {
        "SW": ("key opening", None), "ENC1": ("opening", None),
        "OLED1": ("window", None), "J1": ("USB notch", None),
        "J2": ("access hatch", None), "SW25": ("side notch", None),
        "SW26": ("press holes", None),
        "U1": ("U1 pocket", U1_CEIL - LID_BOT),
        "TP1": ("solid 1.0mm skin", TOUCH_CEIL - LID_BOT),
        "BT1": ("bottom pocket", BAT_DEPTH),
    }
    default = ("relief", LID_RELIEF_CEIL - LID_BOT)
    print(f"\n{'ref':<14}{'height':>7}  {'treatment':<18}{'clearance':>10}  result")
    failures = []
    for p in parts:
        h = p.get("h")
        if h is None:
            continue
        mode, clr = modes.get(p["ref"], default)
        if clr is None:
            res = "PASS (open)"
        elif clr - (h + 0.2) >= -1e-6:
            res = f"PASS (+{clr - h:.2f})"
        else:
            res = "FAIL"
            failures.append(p["ref"])
        print(f"{p['ref']:<14}{h:>7.2f}  {mode:<18}{'-' if clr is None else f'{clr:.2f}':>10}  {res}")
    if failures:
        raise SystemExit(f"height verification FAILED: {failures}")
    print("height verification: all parts clear\n")


# ---------------- build ----------------
def main():
    a = parse_args()
    pos = json.load(open(a.positions))
    parts = load_parts(a.parts)
    verify_heights(parts)

    b = pos["board"]
    W, H, RAD = b["x1"] - b["x0"], b["y1"] - b["y0"], b["corner_r"]
    HOLES = [tuple(v) for _, v in sorted(pos["holes"].items())]
    usb_x = pos["usb"]["x"]
    ex, ey = pos["ctrl"]["ENC1"]["pos"]
    tx, ty = pos["ctrl"]["TP1"]["pos"]
    gx0, gy0, gx1, gy1 = pos["ctrl"]["OLED1"]["glass"]
    jx0, jy0, jx1, jy1 = pos["ctrl"]["J2"]["bbox"]
    ux0, uy0, ux1, uy1 = pos["ctrl"]["U1"]["bbox"]
    psy = pos["ctrl"]["SW25"]["pos"][1]
    bx0, by0, bx1, by1 = pos["battery"]

    bpy.ops.wm.open_mainfile(filepath=a.blend)
    for o in list(bpy.data.objects):
        if o.name.startswith(("CaseBottom", "CaseTop", "CoverPlug")):
            bpy.data.objects.remove(o, do_unlink=True)

    # ------------ bottom: floor + walls + battery pocket + bosses ------------
    bot = rbox(-WALL, W + WALL, -WALL, H + WALL, BOT_Z, LID_BOT, RAD)
    bot.name = "CaseBottom"
    bl(bot, rbox(-CLR, W + CLR, -CLR, H + CLR, -CAV, LID_BOT + 0.2, RAD - 2), 'DIFFERENCE')
    bl(bot, rbox(bx0, bx1, by0, by1, -BAT_DEPTH, -CAV + 0.1, 2.0), 'DIFFERENCE')  # battery
    bl(bot, rbox(usb_x - USB_HALF_W, usb_x + USB_HALF_W, -WALL - 2, 1,
                 -0.6, LID_BOT + 0.1, 1.2), 'DIFFERENCE')                          # USB
    bl(bot, box(ux0 - 0.5, ux1 + 0.5, -WALL - 2, 1, 1.3, LID_BOT + 0.1), 'DIFFERENCE')  # antenna
    bl(bot, box(W - 1.5, W + WALL + 1, psy - 5.5, psy + 5.5, 1.1, LID_BOT + 0.1),
       'DIFFERENCE')                                                               # power switch
    for hx, hy in HOLES:
        bl(bot, cyl(hx, hy, -CAV, 0.0, BOSS_D / 2), 'UNION')
        bl(bot, cyl(hx, hy, -(INS_LEN + RELIEF), 0.01, PILOT / 2), 'DIFFERENCE')
    mb = bpy.data.materials.get("BotMat") or bpy.data.materials.new("BotMat")
    mb.diffuse_color = (0.10, 0.10, 0.12, 1)
    if not bot.data.materials:
        bot.data.materials.append(mb)

    # ------------ lid: plate + reliefs + openings + screw columns ------------
    top = rbox(-WALL, W + WALL, -WALL, H + WALL, LID_BOT, LID_TOP, RAD)
    top.name = "CaseTop"
    # global underside relief (before the columns so they stay full height)
    bl(top, rbox(1.5, W - 1.5, 1.5, H - 1.5, LID_BOT - 0.5, LID_RELIEF_CEIL, 4.0),
       'DIFFERENCE')
    # ESP32-S3 module pocket (0.5 mm skin) + open antenna slot through the edge
    bl(top, rbox(ux0 - 0.5, ux1 + 0.5, -1.0, uy1 + 1.0, LID_BOT - 0.5, U1_CEIL, 1.0),
       'DIFFERENCE')
    bl(top, box(ux0 - 0.5, ux1 + 0.5, -WALL - 2, -0.5, LID_BOT - 1, LID_TOP + 1),
       'DIFFERENCE')
    # touch zone: thin to 1.0 mm from below, engrave finger-guide ring on top
    bl(top, cyl(tx, ty, LID_BOT - 0.5, TOUCH_CEIL, TOUCH_POCKET_R), 'DIFFERENCE')
    bl(top, torus(tx, ty, LID_TOP, GUIDE_R, GUIDE_GROOVE), 'DIFFERENCE')
    # key openings sized to the Choc body; the caps overhang and float above
    hk = (SW_BODY + FIT) / 2
    for ref, (kx, ky) in pos["keys"].items():
        bl(top, rbox(kx - hk, kx + hk, ky - hk, ky + hk, LID_BOT - 1, LID_TOP + 1, 0.8),
           'DIFFERENCE')
    # encoder opening (measured EC11 body 11.7 x 14.7 + clearance, V1 dims)
    enc_w, enc_d = 11.70 + FIT, 14.70 + FIT
    bl(top, rbox(ex - enc_w / 2, ex + enc_w / 2, ey - enc_d / 2, ey + enc_d / 2,
                 LID_BOT - 1, LID_TOP + 1, 0.8), 'DIFFERENCE')
    # OLED: through window (glass + 0.6) + 1.0 mm cover-glass ledge on top
    c = OLED_CLR / 2
    bl(top, rbox(gx0 - c, gx1 + c, gy0 - c, gy1 + c, LID_BOT - 1, LID_TOP + 1, 1.0),
       'DIFFERENCE')
    bl(top, rbox(gx0 - c - LEDGE_W, gx1 + c + LEDGE_W, gy0 - c - LEDGE_W,
                 gy1 + c + LEDGE_W, LID_TOP - LEDGE_DEPTH, LID_TOP + 1, 1.0),
       'DIFFERENCE')
    # USB notch, power-switch notch, J2 battery-connector hatch, BOOT/RESET holes
    bl(top, box(usb_x - USB_HALF_W, usb_x + USB_HALF_W, -WALL - 2, 3,
                LID_BOT - 1, LID_TOP + 1), 'DIFFERENCE')
    bl(top, box(W - 5.5, W + WALL + 1, psy - 5.5, psy + 5.5,
                LID_BOT - 1, LID_TOP + 1), 'DIFFERENCE')
    bl(top, rbox(jx0 - 0.8, jx1 + 0.8, jy0 - 0.8, jy1 + 0.8,
                 LID_BOT - 1, LID_TOP + 1, 1.0), 'DIFFERENCE')
    for tref in ("SW26", "SW27"):
        px, py = pos["ctrl"][tref]["pos"]
        bl(top, cyl(px, py, LID_BOT - 1, LID_TOP + 1, TACT_HOLE_R), 'DIFFERENCE')
    # screw columns with countersink + plug seat (V1 system, encoder-aware)
    enc_hw, enc_hh = enc_w / 2, enc_d / 2
    for hx, hy in HOLES:
        dx = max(0.0, abs(hx - ex) - enc_hw)
        dy = max(0.0, abs(hy - ey) - enc_hh)
        room = math.hypot(dx, dy)
        col_d = BOSS_D if room >= BOSS_D / 2 + 0.3 else max(CBORE_D + 0.9, 2 * (room - 0.05))
        bl(top, cyl(hx, hy, LID_BOT, LID_TOP, col_d / 2), 'UNION')
        bl(top, cyl(hx, hy, LID_BOT - 0.5, CS_START, SHANK_CLR / 2), 'DIFFERENCE')
        bl(top, cone(hx, hy, CS_START, CS_END, SHANK_CLR / 2, CBORE_D / 2), 'DIFFERENCE')
        bl(top, cyl(hx, hy, PLUG_FLOOR, LID_TOP + 0.5, PLUG_D / 2 + 0.1), 'DIFFERENCE')
        print(f"  column ({hx},{hy}) encoder room {room:.1f} -> O{col_d:.1f}")
    top = deisl(top)
    top.name = "CaseTop"
    mt = bpy.data.materials.get("TopMat") or bpy.data.materials.new("TopMat")
    mt.diffuse_color = (0.16, 0.16, 0.19, 1)
    if not top.data.materials:
        top.data.materials.append(mt)

    # ------------ cover plugs (press fit) ------------
    plugs = []
    for i, (hx, hy) in enumerate(HOLES):
        p = cyl(hx, hy, PLUG_FLOOR + 0.05, LID_TOP - 0.05, PLUG_D / 2)
        p.name = f"CoverPlug_{i}"
        if not p.data.materials:
            p.data.materials.append(mt)
        plugs.append(p)

    print(f"\ncase outer {W + 2 * WALL:.1f} x {H + 2 * WALL:.1f} x {LID_TOP - BOT_Z:.1f} mm"
          f" | cavity {CAV:.1f} below PCB, battery pocket {bx1 - bx0:.0f}x{by1 - by0:.0f}"
          f" to {BAT_DEPTH:.1f} below PCB"
          f" | insert M2.5x{INS_LEN} OD{INS_OD} pocket O{PILOT}x{INS_LEN + RELIEF}"
          f" | screw M2.5x8 csk O{SCREW_HEAD_D}x{SCREW_HEAD_H}"
          f" | plug O{PLUG_D - 0.2:.1f}x{PLUG_DEPTH - 0.1:.1f}")

    out = a.outdir.rstrip("/")
    exports = [(bot, out + "/case-bottom.stl"), (top, out + "/case-top-lid.stl"),
               (plugs[0], out + "/case-cover-plug.stl")]
    for o, path in exports:
        mesh_cleanup(o)
        nm = nonmanifold_edges(o)
        print(f"manifold check {o.name}: {nm} non-manifold edges "
              f"{'PASS' if nm == 0 else 'FAIL'}")
        exp(o, path)
        print("wrote", path)
    top.hide_set(True)
    top.hide_viewport = True
    top.hide_render = True
    bpy.ops.wm.save_mainfile()
    print("CASE DONE")


main()
