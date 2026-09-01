# AgentDeck V2: Wireless AI Control Deck (20 keys, ESP32-S3, BLE + USB-C)

> Method: script-generated KiCad (v2/tools, tracked in git), freerouting, home hand
> assembly with parts ordered from JLCPCB/LCSC. V2 is the wireless platform decided in
> docs/ROADMAP.md: V1's control-surface identity on the ESP32-S3 / LiPo platform that
> was designed (never built) as "V3" before the 2026-08-30 reset - see git history.

## Version naming (authoritative)

| Version | What it is | Where |
|---|---|---|
| V1 | 95x95 4-layer RP2040 board, 13 keys, USB only. The wired testbed | `v1/` |
| V2 | THIS: 20 keys (4x5), ESP32-S3, OLED, joystick, 2000 mAh LiPo, USB-C + BLE | `v2/` |

The pre-reset V2 (PowerDeck two-deck concept) and V3/V4 paper designs were deleted at
commit 297fabb; this V2 recovers the V3 platform work.

## Feature set (docs/ROADMAP.md, V2 section)

20-key 4x5 Choc matrix (row 0 = fixed system row: INT / PTT / REC / MODE / DND;
rows 1-3 assignable: 8 agent keys + 7 action keys) · per-key SK6812 · 0.96" OLED
(mode / agent state / battery / rate-limit runway) · EC11 encoder · Alps 5-way
joystick (carried from V1) · USB-C + BLE HID, cable wins when plugged · protected
2000 mAh 103450 LiPo, TP4056 charge + AO3401A load share (run-while-charging) ·
power switch · same host protocol as V1 (`v1/host/agentdeck_bridge.py`) + screen cmd.

Deviations from the roadmap's first sketch, decided during generation: the charger
stays TP4056 + load-share FET rather than a BQ24074-class power-path IC, and battery
level stays an ADC divider rather than a fuel-gauge IC - both alternatives are
QFN/DFN parts that break the hand-solder floor (0.5 mm pitch, no exposed-pad-only
packages). Swap them in if the board ever moves to JLCPCB assembly. The V3 touch pad
is gone: PTT is a mechanical key in the system row.

## Architecture

```
USB-C (J1) ─ USBLC6 ESD ─ D+/D- ──────────────► ESP32-S3-WROOM-1 (U1)
   │ VBUS 5V                                      │ GPIO matrix 4 rows × 5 cols (20 keys
   ├──► TP4056 (U4) ──► BAT+ ──► JST-PH (J2) ─ LiPo│   + 20× 1N4148W)
   │        │ PROG 2.4k = 500 mA                  │ I2C → OLED (OLED1)
   │        └ CHRG/STDBY → status nets            │ GPIO15/16/17/18/1 ← SKQUCAA010 joystick
   ├──► Q1 AO3401A gate (load share: USB present  │ GPIO → EC11 A/B/SW
   │      disconnects battery from VSYS)          │ GPIO → LED_DATA → U2 AHCT125 → chain
   ▼                                              │ ADC → VBAT ÷ (100k/47k)
  VSYS (5V USB or 3.7–4.2V battery, diode-OR) ────┤ EN/IO0 ← BOOT/RESET tacts + prog pads
   ├──► SK6812 ×20 power rail (3.7–5.5V OK)       │
   └──► ME6211C33 (U5) ──► +3V3 ──► U1, OLED, pulls
        (low-Iq LDO; power switch SW25 in VSYS path)
```

Key GPIO budget (S3): 4+5 matrix, 2 I2C, 5 joystick, 3 encoder, 1 LED data, 1 ADC,
2 status (CHRG/STDBY sense), spare 2 (GPIO38/39). Strapping pins (GPIO0/3/45/46) kept free of
matrix duty per datasheet §strapping.

## Component placement rules (datasheet-driven)

Datasheets live in `docs/datasheets/` (V1 set) and `docs/datasheets/v2/`:
`esp32-s3-wroom-1_datasheet.pdf`, `esp32-s3-hw-design-guidelines.pdf`, `tp4056.pdf`,
plus V1's `sk6812mini-e.pdf`. ME6211 + AO3401A sheets: fetch at order
time (LCSC links rotated). `v2/tools/place_pcb.py` implements these as constraints:

1. **ESP32-S3-WROOM antenna** (HW design guidelines §PCB layout): antenna end
   overhangs the board edge, or sits on an edge with **≥15 mm copper keepout** on all
   layers under/around the antenna; no traces, no pour, no silk. Module GND pad
   stitched with vias to bottom pour.
2. **Decoupling** (guidelines §power): 100 nF within **2 mm** of each module 3V3 pin;
   10 µF bulk within 10 mm; LDO in/out caps at the LDO pads (ME6211 needs ≥1 µF
   ceramic on out, X5R/X7R).
3. **USB differential pair** (V1 lore + guidelines): D+/D− routed as a coupled pair,
   length-matched ±0.5 mm, over solid ground, no layer change between connector, ESD
   part, and module; ESD diode (U3) placed at the connector, stubs minimized. On a
   2-layer 1.6 mm board true 90 Ω is not achievable, keep the pair **short (<15 mm)**
   which is fine at full-speed USB (V1 shipped the same compromise, documented).
4. **TP4056 thermal** (tp4056.pdf): it is a linear charger and dissipates
   (VBUS−VBAT)·Icharge ≈ 0.6 W worst case at 500 mA. Copper pour on its tab/GND pins
   ≥1 cm², thermal vias to bottom pour; keep ≥5 mm from the battery pocket.
5. **SK6812 chain** (sk6812mini-e.pdf): 100 nF per LED at its VDD; power injected at
   both chain ends (20 LEDs ≈ 1.2 A worst-case white, VSYS pour, not a trace);
   data line series 330 R at the head; keep data stubs < 5 mm.
6. **Joystick** (Alps SKQUCAA010, THT snap-in): right-hand strip below the battery
   pocket, clear of the key field; directions are plain GPIO inputs with internal
   pullups, COM to GND - no special copper rules.
7. **Matrix diodes**: cathode to row (COL2ROW), consistent orientation for firmware;
   diode next to its switch pad, not bussed at a distance.
8. **Load-share FET** (NeuralCard DESIGN.md §3): Q1 gate to VBUS with 100 k bleed,
   source to VSYS, drain to BAT side, battery isolated when USB present; place at
   the power entry corner with the TP4056.
9. **EC11/tacts/power switch**: mechanical parts on board edges per their drawings;
   MSK12C02 actuator overhangs the edge (NeuralCard pattern).
10. **OLED FPC tab**: solder tab lands on top edge strip; keep the flex bend radius
    area free of components for 5 mm behind the tab.

## PCB best practices adopted (2-layer)

Decision 2026-09-01: V2 stays 2-layer. The scripted flow (freerouting +
finish_v2 repair) closes all but a handful of links at this density; those
leftovers are hand-routed in KiCad and recorded in the changelog. The USB
pair and the module decoupling comb are pre-routed and locked by place_pcb so
they survive re-runs.


- **Bottom layer = near-solid GND pour**; top pour GND in gaps; stitch vias on a
  ~10 mm grid and around every connector/IC (return-path rule: every signal has an
  adjacent ground return).
- Power distribution as pours/wide traces: VSYS pour region on top around the LED
  field; 3V3 min 0.5 mm trace ring.
- All vias ≥ 0.45/0.3 mm (standard fab bracket, pricing lesson from V1 rev0.1).
- Track/clearance defaults 0.2/0.2 mm (hand-friendly, easy fab); 0.15 only where the
  OLED tab forces it.
- Silkscreen: every ref + pin-1 marks + polarity bars; flashing instructions and
  pinout legend printed on the board (V1 style); text ≥1 mm height (JLC legibility , 
  V1 DRC lesson).
- No components under the battery pocket footprint (keepout zone in the PCB and a
  matching pocket in the case bottom). V2 pocket: 34 x 50 mm on the right-hand strip
  (x 108-142, y 12-62) for a 103450 cell; the key field ends at x ≈ 110.

## Firmware (v2/firmware, Arduino ESP32-S3)

Matrix scan/debounce → USB HID *and* BLE HID (NimBLE), auto-switch by USB presence;
OLED status UI; joystick edges → host (`J` lines); system-row roles → host (`K` lines); SK6812 state colors (V1 language: idle/think/
work/block/done/err); battery % from ADC; CDC protocol = V1's plus `S <line> <text>`.
USB name "AgentDeckV2" (agentdeck_bridge.py matches by name).

## Rules recap (see v2/PARTS.yaml header)

Manifest-first · 2D+3D dims verified by v2/tools/verify_parts.py · hand-solder floor
0.5 mm pitch · JLC/LCSC stock status per line · V1 untouched · v2 tools tracked.
