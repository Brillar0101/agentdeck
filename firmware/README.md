# ClaudeMicro Firmware

CircuitPython firmware turning the board into an agent-control surface, plus a
host bridge that drives the agent keys from real agent activity.

An Arduino/C++ port with identical behaviour lives in
[`arduino/`](arduino/README.md) if you prefer a compiled build over
CircuitPython.

## Install

1. Hold **BOOT**, plug in USB-C → the `RPI-RP2` drive appears.
2. Copy the [CircuitPython 9.x UF2 for Raspberry Pi Pico](https://circuitpython.org/board/raspberry_pi_pico/)
   onto it (the generic Pico build is correct — all pins used are GP0–GP24).
3. From the [Adafruit CircuitPython bundle](https://circuitpython.org/libraries),
   copy into `CIRCUITPY/lib/`: `adafruit_hid/` and `neopixel.mpy`.
4. Copy `boot.py` and `code.py` to the `CIRCUITPY` root, then replug.

## What each control does

```
    [ DIAL ]   ACCEPT   REJECT    [ JOYSTICK ]
    AGENT1     AGENT2   AGENT3    AGENT4
    AGENT5     AGENT6   NEWCHAT   MODEL
    FN        [ PUSH-TO-TALK ]    MACRO
```

| Control | Action | Sends |
|---|---|---|
| **Agent 1–6** | select that agent; the key colour *is* its live state | `Ctrl+Alt+1`…`6` |
| **Accept** | approve the agent's changes | `Ctrl+Alt+Enter` |
| **Reject** | interrupt / decline | `Ctrl+Alt+Backspace` |
| **New chat** | start a fresh session | `Ctrl+Alt+N` |
| **Model** | cycle model | `Ctrl+Alt+M` |
| **Push-to-talk** | wide key, **held** while dictating | `Ctrl+Alt+Space` (held) |
| **Macro** | free slot | `Ctrl+Alt+X` |
| **FN** | hold for a second layer (adds Shift to any chord) | — |
| **Dial** | reasoning effort up / down | `Ctrl+Alt+=` / `Ctrl+Alt+-` |
| **Dial press** | cycle thinking mode | `Ctrl+Alt+T` |
| **Joystick** | navigate | `Ctrl+Alt+I/K/J/L`, centre `Ctrl+Alt+O` |

Ctrl+Alt chords were chosen so nothing collides with normal typing. Rebind by
editing `BINDINGS`, `DIAL_*` and `JOY_BIND` at the top of `code.py`.

## Agent-state colours

| State | Colour |
|---|---|
| `idle` | dim violet |
| `think` | amber, pulsing |
| `work` | orange |
| `block` | **red, blinking** — wants your attention |
| `done` | green |
| `err` | magenta |

Only the six agent keys show state; the other keys carry a steady hint colour
and brighten while FN is held. The FN key (SW14) has its own LED: dim white at
rest, bright white while the layer is active.

## Host bridge

```bash
pip install pyserial
python3 ../host/claude_bridge.py demo             # cycle every state
python3 ../host/claude_bridge.py agent 3 block    # agent 3 red/blinking
python3 ../host/claude_bridge.py all done         # all six green
python3 ../host/claude_bridge.py watch            # print key/dial/joystick events
```

Wire it to Claude Code with hooks — a ready-to-paste `settings.json` snippet is
in the header of `host/claude_bridge.py` (UserPromptSubmit → thinking,
PreToolUse → working, Notification → blocked, Stop → done).

## Hardware map

| Function | GPIO |
|---|---|
| SW1–SW12 | GP0–GP11 |
| SW14 (FN, bottom-left) | GP20 |
| Dial A / B / press | GP12 / GP13 / GP14 |
| Joystick U/D/L/R / centre | GP15–GP18 / GP19 |
| SK6812 chain (13 LEDs) | GP21 |
| Aux LEDs link / activity / error | GP22 / GP23 / GP24 |

## Verify on first hardware

Three things can only be confirmed with a real board — each is a one-line change:

- **Joystick direction order** — `JOY_NAMES = "UDLRC"`; reorder if up/down/left/right feel wrong.
- **LED chain order** — indices assume the chain runs SW1→SW12; check with `all done`.
- **Aux LED polarity** — they're driven active-high.
