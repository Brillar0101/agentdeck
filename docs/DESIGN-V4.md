# ClaudeMicro V4 — Voice + Screen AI Control Deck

> Method unchanged from V3: script-generated KiCad (v4/tools, tracked),
> freerouting + finish pipeline, home hand assembly, manifest-first
> (`v4/PARTS.yaml` is the single source of truth, verified by tools).
> V1/V2/V3 untouched; V4 lives in `v4/`.

## Version naming (authoritative)

| Version | What it is | Where |
|---|---|---|
| V1 | 90x90 4-layer RP2040, JLC-assembled (rev 0.1, ordered) | `hardware/` |
| V2 | PowerDeck two-deck concept (pogo/Qi) — paper design | separate repo |
| V3 | 150x110 2-layer ESP32-S3, 24 keys, OLED, touch, LiPo, USB+BLE | `v3/` |
| V4 | THIS: V3 platform + voice (wake word/PTT audio) + 1.69" touch LCD + 2nd encoder | `v4/` |

## What V4 adds over V3 (and why)

| Delta | Why |
|---|---|
| I2S MEMS mic + on-device wake word (ESP-SR) | "hey Claude" -> PTT stream to the host bridge; the deck's defining AI feature |
| NS4168 2.5W class-D amp + speaker | agent notifications audible; voice feedback |
| 1.69" 240x280 ST7789 touch LCD replaces the 0.96" OLED | soft-key zone + richer agent status; ALSO fixes the OLED's sourcing fragility (2 pcs episode) |
| second EC11 encoder | volume/PTT gain on one, layer/scroll on the other |
| keeps: 4x6 Choc matrix, per-key SK6812, touch PTT pad, TP4056+AO3401A+ME6211 power tree, USB-C+BLE, 1000 mAh LiPo | proven V3 blocks, same footprints, same tools |

Board stays ~150x110 2-layer. The top strip gains the LCD (window in lid) and
mic port; the speaker lives in a small case chamber over the battery bump.

## Architecture deltas

```
V3 power tree unchanged (USB-C -> TP4056 -> AO3401A load share -> VSYS -> ME6211 3V3)
ESP32-S3-WROOM-1-N8R2
  I2S0 full duplex: BCLK+WS shared, DIN <- MEMS mic, DOUT -> NS4168 -> speaker
  SPI: LCD ST7789 (SCK MOSI DC CS RST BL)   I2C: LCD touch (CST816-class) INT
  4x6 matrix / SK6812 chain / VBAT ADC / touch pad PTT / 2x EC11 = V3 pattern
```

GPIO budget: V3 spares (IO16/17/18, IO35-39) + repurposed CHRG/STDBY (IO47/48)
+ careful post-boot use of strapping IO3/45/46 cover LCD(6) + touch INT(1) +
I2S(4, full-duplex shared clocks) + ENC2(3). Tight but closed; exact map is a
Phase 1 deliverable printed by the generator (V3 rule: pins.h diffs against it).

## Component placement rules (adds to V3 rules 1-10)

11. **MEMS mic** (bottom-ported): port hole >=0.8 mm through the PCB, no
    copper/mask ring around the port, keep >=10 mm from the speaker and away
    from SK6812 switching noise; gasket land on the case floor.
12. **Speaker**: faces a case chamber with grille slots over the battery bump
    region; keep the amp (NS4168) within 15 mm of the speaker connector; amp
    EP tied to GND pour with the TP4056 thermal via pattern.
13. **LCD**: FPC/module tab on the top strip like the V3 OLED (rule 10
    applies); lid gets a stepped window with cover-glass ledge; touch INT
    routed away from LED data.
14. **Audio vs RF**: I2S lines short and bundled; keep the whole audio corner
    (mic/amp/speaker) on the opposite side of the board from the antenna.

## Sourcing status (live-checked 2026-07-29, see v4/PARTS.yaml)

- NS4168 (C910588): CONFIRMED, 3,230 pcs, ESOP-8-EP = same hand-solder class
  as our TP4056.
- MEMS I2S mic: MSM261S4030H0R (C2840615) page is DEAD at LCSC — VERIFY line
  with alternates (MSM261DGT003 C48227730 is PDM not I2S; external INMP441
  breakout is the fallback, ubiquitous).
- 1.69" ST7789 240x280 touch module: not a native LCSC catalog item — VERIFY
  line, two paths: LCSC bare panel + 0.5 mm FPC connector (within the V3
  hand-solder floor), or the ubiquitous external 8-pin header module
  (same mounting trick as the V3 OLED fallback).
- Everything carried from V3 was live-confirmed 2026-07-29.

## Phases (V3 playbook, per-phase gates)

0. Scaffold + manifest (this doc, v4/PARTS.yaml, tools copied/parameterized)
1. Schematic gen — ERC 0; pinout table printed and mirrored into firmware
2. PCB gen + routing — freerouting pipeline + finish_v4; DRC 0/0;
   verify_parts green (audio placement rules 11-14 as constraints)
3. Firmware — V3 base + ESP-SR wake word ("hey Claude" custom or "hi ESP"
   stock), I2S duplex, LVGL or plain ST7789 UI, `S`-protocol superset;
   compile gate + wake-word smoke test documented
4. Enclosure — V3 case generator + LCD window, mic gasket boss, speaker
   chamber + grille; dressed assembly render
5. Fab + order — gerbers, gated order list, live stock pass

## Non-goals (scope by exclusion)

- No display-per-key, no hall-effect switches, no JLC-assembly branch (that
  is the V5 "pro" fork decision, not V4)
- No Qi coil in V4 (pocket reserved; PowerDeck concept stays parked)
- No mesh/Matter/HA integration; host protocol stays the V1 CDC line protocol
