# ClaudeMicro Firmware

CircuitPython firmware for the ClaudeMicro RP2040 macropad, plus a host bridge
that mirrors Claude Code agent state onto the per-key RGB LEDs.

## Install

1. Hold **BOOT** on the board, plug in USB-C → `RPI-RP2` drive appears.
2. Copy the [CircuitPython 9.x UF2 for Raspberry Pi Pico](https://circuitpython.org/board/raspberry_pi_pico/)
   onto the drive (generic Pico build works; all pins used are standard GP0-24).
3. From the [Adafruit CircuitPython bundle](https://circuitpython.org/libraries),
   copy to `CIRCUITPY/lib/`:
   - `adafruit_hid/`
   - `neopixel.mpy`
4. Copy `boot.py` and `code.py` from this directory to the `CIRCUITPY` root.
5. Unplug/replug. The keys type F13-F24, encoder does volume, joystick does
   arrows/Enter, touch pad sends F24.

## Pin map (from the PCB netlist)

| Function | GPIO |
|---|---|
| SW1..SW12 (C L A U D E / F1-F4 / GO / FN) | GP0..GP11 |
| Encoder A / B / push | GP12 / GP13 / GP14 |
| Joystick A B C D / centre | GP15-GP18 / GP19 |
| Touch sensor out (TTP223) | GP20 |
| SK6812 LED chain (12, via level shifter) | GP21 |
| Aux LEDs: link / activity / error | GP22 / GP23 / GP24 |

## Host bridge (agent-status LEDs)

```
pip install pyserial
python3 ../host/claude_bridge.py demo        # cycle all LED states
python3 ../host/claude_bridge.py set 0 work  # key 1 orange
python3 ../host/claude_bridge.py all done    # everything green
```

Wire it to Claude Code via hooks — see the header of `../host/claude_bridge.py`
for a ready-to-paste `settings.json` snippet (PreToolUse → working,
Notification → blocked, Stop → done).

States: `idle` dim purple · `think` amber pulse · `work` orange ·
`block` red · `done` green · `err` magenta · `off`.

## Things to verify on first hardware

- Joystick direction order (`JOY_NAMES` in code.py) — swap letters if U/D/L/R
  feel wrong.
- LED chain order (`LED_ORDER`) — if key lights don't match key positions,
  reorder that list.
- Touch polarity: TTP223 boards vary; if touch reads inverted, change the
  pull and comparison in code.py.
