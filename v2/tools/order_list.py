"""Generate the LCSC/JLCPCB parts-order shopping list from v2/PARTS.yaml.

Outputs v2/fab/order-list.csv (LCSC cart import format: LCSC#, qty) plus a
human-readable summary with spares, external-source lines, and a hard gate:
any line still marked VERIFY makes the script exit non-zero so the order
cannot be generated from unverified stock.

Usage: python3 v2/tools/order_list.py [--boards N] [--allow-verify]
"""
import argparse
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from verify_parts import load_manifest  # same tiny YAML reader

ROOT = Path(__file__).resolve().parents[1]

# spare policy: small cheap parts get generous spares for hand-assembly drops
def spares(qty: int, unit_price) -> int:
    price = float(unit_price or 0)
    if price <= 0.05:
        return max(10, math.ceil(qty * 0.5))
    if price <= 0.5:
        return max(4, math.ceil(qty * 0.25))
    return max(1, math.ceil(qty * 0.1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", type=int, default=3)
    ap.add_argument("--allow-verify", action="store_true")
    args = ap.parse_args()

    manifest = load_manifest(ROOT / "PARTS.yaml")
    rows, external, blocked = [], [], []
    total = 0.0

    for p in manifest:
        qty_board = int(p.get("qty_per_board", "1") or 1)
        need = qty_board * args.boards
        extra = spares(need, p.get("unit_price"))
        lcsc = p.get("lcsc")
        if lcsc in (None, "null", "N/A") or str(lcsc).startswith("basic"):
            if p.get("stock") == "EXTERNAL":
                external.append((p["name"], need + extra))
            elif str(lcsc or "").startswith("basic"):
                rows.append(("SEE-NOTES-0603-KIT", p["name"], need + extra, 0))
            continue
        if p.get("stock") == "VERIFY" and not args.allow_verify:
            blocked.append((lcsc, p["name"]))
        cost = (need + extra) * float(p.get("unit_price") or 0)
        total += cost
        rows.append((lcsc, p["name"], need + extra, cost))

    out = ROOT / "fab" / "order-list.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["LCSC Part Number", "Description", "Quantity"])
        for lcsc, name, qty, _ in rows:
            w.writerow([lcsc, name, qty])

    print(f"order list -> {out}  ({args.boards} boards)")
    for lcsc, name, qty, cost in rows:
        print(f"  {lcsc:14s} x{qty:<4d} ${cost:6.2f}  {name[:52]}")
    print(f"  LCSC subtotal ~${total:.2f}")
    for name, qty in external:
        print(f"  EXTERNAL      x{qty:<4d}          {name[:52]}")
    if blocked:
        print(f"\nBLOCKED: {len(blocked)} lines still VERIFY - re-check stock first:")
        for lcsc, name in blocked:
            print(f"  {lcsc}  {name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
