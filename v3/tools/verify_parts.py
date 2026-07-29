"""Cross-check the V3 PCB against v3/PARTS.yaml (the single source of truth).

Checks, per manifest entry that maps to board footprints:
  1. every footprint's courtyard/bbox X x Y is within TOL of the manifest dims_2d
  2. every footprint has a 3D model assigned (so the Blender assembly is honest)
  3. reports parts whose stock status is not CONFIRMED (gate for Phase 5 ordering)

Run with KiCad's bundled python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/\
Current/bin/python3 v3/tools/verify_parts.py [board.kicad_pcb]

Exits non-zero on any dimension/model failure. Stock warnings do not fail the
build (they fail the ORDER - Phase 5 refuses on non-CONFIRMED lines).

PARTS.yaml is parsed with a deliberately tiny reader (KiCad python has no PyYAML);
it understands only the flat "- key: value" list structure used in that file.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # .../v3
DEFAULT_BOARD = ROOT / "hardware" / "ClaudeMicroV3.kicad_pcb"
TOL_MM = 0.5


def load_manifest(path):
    parts, cur = [], None
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        if re.match(r"^  - ref_prefix:", line):
            cur = {}
            parts.append(cur)
        if cur is None or not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^ {2,4}(?:- )?(\w+): (.+?)(?:\s+#.*)?$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "dims_2d":
            nums = re.findall(r"[\d.]+", val)
            cur[key] = [float(nums[0]), float(nums[1])] if len(nums) >= 2 else None
        elif key in ("height_3d", "unit_price", "pitch_mm"):
            try:
                cur[key] = float(val)
            except ValueError:
                cur[key] = None
        else:
            cur[key] = val.strip('"')
    return parts


def main():
    board_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BOARD
    manifest = load_manifest(ROOT / "PARTS.yaml")
    print(f"manifest: {len(manifest)} part classes")

    not_confirmed = [p for p in manifest
                     if p.get("stock") not in ("CONFIRMED", "EXTERNAL", "N/A")]
    for p in not_confirmed:
        print(f"  STOCK VERIFY NEEDED: {p.get('name')} ({p.get('lcsc')})")

    if not board_path.exists():
        print(f"board not present yet ({board_path}) - manifest-only check done")
        sys.exit(0)

    import pcbnew  # KiCad python only
    board = pcbnew.LoadBoard(str(board_path))
    failures = 0
    by_prefix = {}
    for p in manifest:
        by_prefix[p["ref_prefix"].split("(")[0]] = p
    # tacts are SW26 *and* SW27 (qty 2 on the SW26 manifest line)
    if "SW26" in by_prefix:
        by_prefix.setdefault("SW27", by_prefix["SW26"])

    def dim_candidates(fp):
        """Manifest dims come from datasheets (body or body+leads) - accept a
        match against the fab body outline, the courtyard, or the full
        footprint bbox (all in board plan view)."""
        out = []
        for layers in ((pcbnew.F_Fab, pcbnew.B_Fab),
                       (pcbnew.F_CrtYd, pcbnew.B_CrtYd)):
            bb = None
            for item in fp.GraphicalItems():
                if item.GetLayer() in layers and hasattr(item, "GetBoundingBox"):
                    if isinstance(item, pcbnew.PCB_TEXT):
                        continue
                    ib = item.GetBoundingBox()
                    if bb is None:
                        bb = pcbnew.BOX2I(ib.GetPosition(), ib.GetSize())
                    else:
                        bb.Merge(ib)
            if bb is not None:
                out.append((bb.GetWidth() / 1e6, bb.GetHeight() / 1e6))
        bb = fp.GetBoundingBox(False)
        out.append((bb.GetWidth() / 1e6, bb.GetHeight() / 1e6))
        return out

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        prefix = re.match(r"[A-Za-z]+", ref).group(0)
        # longest matching manifest prefix (e.g. OLED before O)
        entry = None
        for k in sorted(by_prefix, key=len, reverse=True):
            if ref.startswith(k):
                entry = by_prefix[k]
                break
        if entry is None or entry.get("dims_2d") is None:
            continue
        ex, ey = entry["dims_2d"]
        cands = dim_candidates(fp)
        ok = any((abs(w - ex) <= TOL_MM and abs(h - ey) <= TOL_MM) or
                 (abs(w - ey) <= TOL_MM and abs(h - ex) <= TOL_MM)
                 for w, h in cands)                     # allow rotation
        if not ok:
            w, h = cands[0]
            print(f"  DIM FAIL {ref}: board {w:.2f}x{h:.2f} vs manifest {ex}x{ey}")
            failures += 1
        # parts with zero body height (bare copper features) have no 3D body
        if not list(fp.Models()) and entry.get("height_3d") not in (0, 0.0):
            print(f"  3D FAIL  {ref}: no 3D model assigned")
            failures += 1

    print(f"{'FAIL' if failures else 'OK'}: {failures} dimension/model failures, "
          f"{len(not_confirmed)} stock lines needing verification")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
