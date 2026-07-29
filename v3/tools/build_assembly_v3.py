"""Build the ClaudeMicro V3 assembly in Blender: board GLB + 24 switches with
caps + encoder knob + battery placeholder. The case is added by make_case_v3.py.

Pipeline (paths are arguments, nothing hardcoded):
  1. kicad python  v3/tools/export_positions_v3.py --pcb ... --out positions.json
  2. kicad-cli pcb export glb --subst-models --include-tracks --include-pads \
       --include-zones --include-silkscreen --include-soldermask --force \
       -o ClaudeMicroV3.glb ClaudeMicroV3.kicad_pcb
  3. blender -b --python v3/tools/build_assembly_v3.py -- \
       --positions ... --glb ... --assets <repo enclosure dir> --blend <out.blend>
  4. blender -b --python v3/tools/make_case_v3.py -- ...

GLB frame (verified): board mm * 0.001, y negated, PCB underside z=0, top 1.6 mm.
The ChocV1.wrl switch bodies come through the GLB already seated at z 1.6..12.6;
they are only identified and renamed here (V1 needed re-seating, V3 does not).
"""
import argparse
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector

MM = 0.001
CAP_OVER_SWITCH = 2.04   # cap top sits this far above the switch stem top (V1)
KNOB_BOTTOM = 9.0        # knob bottom above PCB top, mm (V1 seat)
PCB_T = 1.6


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", required=True)
    ap.add_argument("--glb", required=True)
    ap.add_argument("--assets", required=True, help="V1 enclosure dir (keycaps/, encoder/)")
    ap.add_argument("--blend", required=True)
    return ap.parse_args(argv)


def world_bbox(o):
    p = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (min(v.x for v in p), max(v.x for v in p), min(v.y for v in p),
            max(v.y for v in p), min(v.z for v in p), max(v.z for v in p))


def import_stl(path):
    before = set(bpy.data.objects)
    try:
        bpy.ops.wm.stl_import(filepath=path, global_scale=0.001)
    except AttributeError:
        bpy.ops.import_mesh.stl(filepath=path, global_scale=0.001)
    return [o for o in bpy.data.objects if o not in before][0]


def find_switches(keys):
    """Geometric-seat heuristic from V1: tall ~15x15 meshes centred on a key."""
    keypts = {ref: (kx * MM, -ky * MM) for ref, (kx, ky) in keys.items()}
    found = {}
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        x0, x1, y0, y1, z0, z1 = world_bbox(o)
        w, d, h = x1 - x0, y1 - y0, z1 - z0
        if not (0.010 < w < 0.020 and 0.010 < d < 0.020 and h > 0.006):
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for ref, (kx, ky) in keypts.items():
            if math.hypot(cx - kx, cy - ky) < 0.004:
                found[ref] = o
                break
    return found


def main():
    a = parse_args()
    pos = json.load(open(a.positions))

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.gltf(filepath=a.glb)

    # ---- switches: identify, rename Switch_NN ----
    sw = find_switches(pos["keys"])
    if len(sw) != len(pos["keys"]):
        raise SystemExit(f"switch heuristic matched {len(sw)}/{len(pos['keys'])} keys")
    sw_top = 0.0
    for ref, o in sw.items():
        o.name = f"Switch_{int(ref[2:]):02d}"
        sw_top = max(sw_top, world_bbox(o)[5])
    print(f"switches identified: {len(sw)}, top z {sw_top / MM:.2f} mm")

    # ---- keycaps ----
    cap_top = sw_top + CAP_OVER_SWITCH * MM
    mat = bpy.data.materials.new("CapMat")
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.93, 0.93, 0.96, 1)
    bs.inputs["Roughness"].default_value = 0.5
    tpl = import_stl(a.assets.rstrip("/") + "/keycaps/cap-normal.stl")
    tpl.data.materials.append(mat)
    for ref, (kx, ky) in pos["keys"].items():
        o = tpl.copy()
        bpy.context.scene.collection.objects.link(o)
        o.name = f"Cap_{ref}"
        bpy.context.view_layer.update()
        x0, x1, y0, y1, z0, z1 = world_bbox(o)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        o.matrix_world = Matrix.Translation(
            Vector((kx * MM - cx, -ky * MM - cy, cap_top - z1))) @ o.matrix_world
    bpy.data.objects.remove(tpl, do_unlink=True)
    print(f"caps placed: {len(pos['keys'])}, cap top {cap_top / MM:.2f} mm")

    # ---- encoder knob ----
    kmat = bpy.data.materials.new("KnobMat")
    kmat.use_nodes = True
    kb = kmat.node_tree.nodes.get("Principled BSDF")
    kb.inputs["Base Color"].default_value = (0.08, 0.08, 0.09, 1)
    kb.inputs["Roughness"].default_value = 0.35
    kb.inputs["Metallic"].default_value = 0.7
    knob = import_stl(a.assets.rstrip("/") +
                      "/encoder/d19h20-knurled-encoder-knobs-champfered-top.stl")
    knob.name = "EncoderKnob"
    knob.data.materials.append(kmat)
    x0, x1, y0, y1, z0, z1 = world_bbox(knob)
    c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    knob.matrix_world = Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, 'X') \
        @ Matrix.Translation(-c) @ knob.matrix_world
    bpy.context.view_layer.update()
    ex, ey = pos["ctrl"]["ENC1"]["pos"]
    x0, x1, y0, y1, z0, z1 = world_bbox(knob)
    knob.matrix_world = Matrix.Translation(Vector((
        ex * MM - (x0 + x1) / 2, -ey * MM - (y0 + y1) / 2,
        (PCB_T + KNOB_BOTTOM) * MM - z0))) @ knob.matrix_world
    print(f"knob at ({ex},{ey}), bottom {PCB_T + KNOB_BOTTOM:.1f} mm")

    # ---- battery placeholder (40x30x8 grey, in the pocket under the PCB) ----
    bx0, by0, bx1, by1 = pos["battery"]
    bcx, bcy = (bx0 + bx1) / 2, (by0 + by1) / 2
    bpy.ops.mesh.primitive_cube_add()
    bat = bpy.context.active_object
    bat.name = "Battery"
    bat.location = (bcx * MM, -bcy * MM, -4.4 * MM)      # z -8.4..-0.4
    bat.scale = (20 * MM, 15 * MM, 4 * MM)
    bpy.ops.object.transform_apply(scale=True)
    bmat = bpy.data.materials.new("BatteryMat")
    bmat.diffuse_color = (0.45, 0.45, 0.47, 1)
    bat.data.materials.append(bmat)
    print(f"battery 40x30x8 at ({bcx:.1f},{bcy:.1f})")

    bpy.ops.wm.save_as_mainfile(filepath=a.blend)
    print("ASSEMBLY DONE ->", a.blend)


main()
