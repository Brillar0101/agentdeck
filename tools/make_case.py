"""ClaudeMicro two-part case with brass heat-set inserts + cover plugs.

Stack-up (matches the reference cross-section), z=0 is the PCB underside.
The lid is deliberately LOW - the keycaps float above it.

     8.0 ---- top of lid ------------------------------
             cover plug  O5.3 x 2.3, sits on the screw head
     5.6 ---------------------------------------------
             M2.5 screw head  O4.5 x 2.5  (bore O5.5)
     3.1 ---- counterbore ledge (1.5 mm of lid under head)
             screw shank, clearance O2.9
     1.6 ---- lid underside rests on PCB top ----------
             PCB 1.6 mm, mounting hole O2.7
     0.0 ---- PCB underside rests on boss -------------
             boss O8.0, insert pocket O3.6 x 5.5 deep
             brass heat-set insert  M2.5 x L4.0 x OD4.0
    -4.0 ---- cavity floor (4.0 mm clears bottom parts)
    -6.4 ---- bottom of case (floor 2.4 mm)

Fasteners (verified against supplier data):
  * Brass heat-set insert  M2.5 x 0.45, OD 4.0 mm, length 4.0 mm
      boss pilot hole 3.6 mm, +1.5 mm relief for displaced plastic / screw tip
  * Screw  M2.5 x 8 mm socket head cap, ISO 4762
      head O4.5 mm, head height 2.5 mm, 2.0 mm hex key
      engagement: 1.5 lid + 1.6 PCB + 4.0 insert = 7.1 mm (M2.5x8)

The top-left lid column is auto-shrunk where the encoder body crowds it.
"""
import bpy, json, math
from mathutils import Vector

MM = 0.001
ROOT = "/Users/barakaeli/kicad-projects/claude-micro/"
SCENE = ROOT + "enclosure/ClaudeMicro-v2-assembled.blend"
pos = json.load(open("/tmp/positions.json"))
USB_ON_TOP = pos["usb"]["top"]
HOLES = [(6, 6), (84, 6), (6, 84), (84, 84)]

# --- hardware ---
INS_OD, INS_LEN = 4.0, 4.0          # heat-set insert
PILOT = 3.6                          # boss pilot hole
SCREW_HEAD_D, SCREW_HEAD_H = 5.0, 1.05   # M2.5 countersunk (ISO 7046), 90 deg
CBORE_D = 5.0                            # top of the countersink
SHANK_CLR = 2.9                     # clearance hole through lid
PLUG_D, PLUG_DEPTH = 4.8, 1.4       # thin plug over the flush screw head
BOSS_D = 8.0                        # ~2x insert OD

# --- case geometry ---
WALL, CLR, CAV, FLOOR = 2.6, 0.5, 4.0, 2.4
LID_BOT, LID_TOP = 1.6, 5.5        # low lid so the caps can travel
CS_START = LID_BOT + 1.35                            # countersink begins here
CS_END = CS_START + SCREW_HEAD_H                     # head flush at this level
PLUG_FLOOR = CS_END                                  # plug sits over the flush head
RELIEF = 1.5                                         # deeper relief for the M2.5x8 tip

bpy.ops.wm.open_mainfile(filepath=SCENE)
for o in list(bpy.data.objects):
    if o.name.startswith(("CaseBottom", "CaseTop", "CoverPlug")):
        bpy.data.objects.remove(o, do_unlink=True)


def box(x0, x1, y0, y1, z0, z1):
    bpy.ops.mesh.primitive_cube_add(); o = bpy.context.active_object
    o.location = ((x0+x1)/2*MM, -(y0+y1)/2*MM, (z0+z1)/2*MM)
    o.scale = ((x1-x0)/2*MM, (y1-y0)/2*MM, (z1-z0)/2*MM)
    bpy.ops.object.transform_apply(scale=True); return o


def cyl(x, y, z0, z1, r, v=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r*MM, depth=(z1-z0)*MM, vertices=v)
    o = bpy.context.active_object; o.location = (x*MM, -y*MM, (z0+z1)/2*MM); return o


def cone(x, y, z0, z1, r_bot, r_top, v=64):
    bpy.ops.mesh.primitive_cone_add(radius1=r_bot*MM, radius2=r_top*MM,
                                    depth=(z1-z0)*MM, vertices=v)
    o = bpy.context.active_object; o.location = (x*MM, -y*MM, (z0+z1)/2*MM); return o


def bl(t, tool, op):
    m = t.modifiers.new("b", 'BOOLEAN'); m.operation = op; m.object = tool
    bpy.context.view_layer.objects.active = t; bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def rbox(x0, x1, y0, y1, z0, z1, r):
    o = box(x0+r, x1-r, y0, y1, z0, z1); bl(o, box(x0, x1, y0+r, y1-r, z0, z1), 'UNION')
    for cx, cy in ((x0+r, y0+r), (x1-r, y0+r), (x0+r, y1-r), (x1-r, y1-r)):
        bl(o, cyl(cx, cy, z0, z1, r), 'UNION')
    return o


def deisl(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    parts = list(bpy.context.selected_objects)
    main = max(parts, key=lambda p: p.dimensions.x*p.dimensions.y)
    for p in parts:
        if p is not main: bpy.data.objects.remove(p, do_unlink=True)
    return main


# ---------------- bottom case: floor + walls + bosses with insert pockets ----
bot = rbox(-WALL, 90+WALL, -WALL, 90+WALL, -(CAV+FLOOR), LID_BOT, 6.0)
bot.name = "CaseBottom"
bl(bot, rbox(-CLR, 90+CLR, -CLR, 90+CLR, -CAV, LID_BOT+0.2, 4.0), 'DIFFERENCE')  # cavity + PCB pocket
if USB_ON_TOP:
    bl(bot, rbox(38, 52, -WALL-2, 1, -0.6, 0.4, 1.2), 'DIFFERENCE')
else:
    bl(bot, rbox(38, 52, -WALL-2, 1, -3.9, 0.4, 1.2), 'DIFFERENCE')       # USB (rear)
for hx, hy in HOLES:
    bl(bot, cyl(hx, hy, -CAV, 0.0, BOSS_D/2), 'UNION')                     # boss
    bl(bot, cyl(hx, hy, -(INS_LEN+RELIEF), 0.01, PILOT/2), 'DIFFERENCE')   # insert pocket
mb = bpy.data.materials.get("BotMat") or bpy.data.materials.new("BotMat")
mb.diffuse_color = (0.10, 0.10, 0.12, 1)
if not bot.data.materials: bot.data.materials.append(mb)

# ---------------- top lid: openings + counterbore + plug pocket -------------
top = rbox(-WALL, 90+WALL, -WALL, 90+WALL, LID_BOT, LID_TOP, 6.0)
top.name = "CaseTop"
# Openings are sized to the COMPONENT BODIES, not the caps: the caps and knob
# float above the lid and overhang these holes, so the lid reads as a solid plate.
SW_BODY, FIT = 15.0, 2.4            # body + 1.0 mm clearance on every side
H = (SW_BODY + FIT)/2
for ref, (kx, ky) in pos["keys"].items():
    bl(top, rbox(kx-H, kx+H, ky-H, ky+H, LID_BOT-1, LID_TOP+1, 0.8), 'DIFFERENCE')
ex, ey = pos["ctrl"]["ENC1"]; jx, jy = pos["ctrl"]["JS1"]
ENC_W, ENC_D = 11.70+FIT, 14.70+FIT      # measured encoder body + clearance
JOY_W = 10.77+FIT                        # measured joystick body + clearance
bl(top, rbox(ex-ENC_W/2, ex+ENC_W/2, ey-ENC_D/2, ey+ENC_D/2, LID_BOT-1, LID_TOP+1, 0.8), 'DIFFERENCE')
bl(top, cyl(jx, jy, LID_BOT-1, LID_TOP+1, JOY_W/2), 'DIFFERENCE')
if USB_ON_TOP:
    bl(top, box(38, 52, -WALL-2, 3, LID_BOT-1, 5.5), 'DIFFERENCE')
ENC_BODY_HW, ENC_BODY_HH = ENC_W/2, ENC_D/2   # from the opening above
for hx, hy in HOLES:
    # shrink this column if the encoder body is close (top-left corner)
    dx = max(0.0, abs(hx-ex)-ENC_BODY_HW); dy = max(0.0, abs(hy-ey)-ENC_BODY_HH)
    room = math.hypot(dx, dy)
    col_d = BOSS_D if room >= BOSS_D/2 + 0.3 else max(CBORE_D+0.9, 2*(room-0.05))
    bl(top, cyl(hx, hy, LID_BOT, LID_TOP, col_d/2), 'UNION')               # corner column
    bl(top, cyl(hx, hy, LID_BOT-0.5, CS_START, SHANK_CLR/2), 'DIFFERENCE')          # shank
    bl(top, cone(hx, hy, CS_START, CS_END, SHANK_CLR/2, CBORE_D/2), 'DIFFERENCE')   # countersink
    bl(top, cyl(hx, hy, PLUG_FLOOR, LID_TOP+0.5, PLUG_D/2+0.1), 'DIFFERENCE')       # plug seat
    print(f"  corner({hx},{hy}) encoder room {room:.2f} -> column O{col_d:.1f}")
top = deisl(top); top.name = "CaseTop"
mt = bpy.data.materials.get("TopMat") or bpy.data.materials.new("TopMat")
mt.diffuse_color = (0.16, 0.16, 0.19, 1)
if not top.data.materials: top.data.materials.append(mt)

# ---------------- cover plugs (4x, press fit) -------------------------------
plugs = []
for i, (hx, hy) in enumerate(HOLES):
    p = cyl(hx, hy, PLUG_FLOOR+0.05, LID_TOP-0.05, PLUG_D/2)
    p.name = f"CoverPlug_{i}"
    if not p.data.materials: p.data.materials.append(mt)
    plugs.append(p)

print(f"case built | insert M2.5x{INS_LEN} OD{INS_OD} pocket O{PILOT}x{INS_LEN+RELIEF}"
      f" | screw M2.5x8 countersunk head O{SCREW_HEAD_D}x{SCREW_HEAD_H}"
      f" | plug O{PLUG_D-0.2}x{PLUG_DEPTH-0.1} | USB_top={USB_ON_TOP}")

def exp(o, p):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    try: bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True, global_scale=1000.0)
    except AttributeError: bpy.ops.export_mesh.stl(filepath=p, use_selection=True, global_scale=1000.0)


exp(bot, ROOT + "enclosure/case-bottom.stl")
exp(top, ROOT + "enclosure/case-top-lid.stl")
exp(plugs[0], ROOT + "enclosure/case-cover-plug.stl")
top.hide_set(True); top.hide_viewport = True; top.hide_render = True
bpy.ops.wm.save_mainfile()
print("CASE DONE")
