# tools

Scripts to regenerate the board's routing, enclosure, and 3D assembly. Run with
KiCad's bundled Python (board scripts) or Blender (`build_assembly`, `make_case`).

| Script | Purpose |
|---|---|
| `finish_full.py <ses>` | Import a routed SES, flood GND on 4 layers, pour the VBUS plane, stitch vias, add mounting holes and switch carriers. The end of the routing pipeline. |
| `add_switch_bodies.py` | Place padless F.Cu carriers holding the Choc switch 3D models (called by `finish_full`). |
| `move_switches_to_grid.py` | Snap the hot-swap sockets so each switch centre lands on the key grid. |
| `make_case.py` | Generate the two-part enclosure (bottom case, plate lid, cover plugs) with M2.5 heat-set-insert bosses; exports STLs. |
| `build_assembly.py` | Build the full Blender scene: board, switches, caps, knob, joystick cap, case. |

`freerouting.jar` is git-ignored — download it from
https://github.com/freerouting/freerouting/releases

Note: freerouting stores a config at `${java.io.tmpdir}/freerouting/freerouting.json`.
It must set `usage_and_diagnostic_data.disable_analytics: true`, or the router
hangs for many minutes at save time trying to phone home.
