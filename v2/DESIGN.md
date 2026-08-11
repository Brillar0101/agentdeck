# AgentDeck V2: PowerDeck (paper design)

V2 is a two-deck system, planned on paper only. Nothing here has been drawn
in KiCad yet.

## Concept

The V1 controller becomes the upper deck. Below it sits a separate PowerDeck:
a second board carrying Qi wireless charging and a Li-ion battery, attached
magnetically, feeding 5 V up to the controller through pogo pins. The result
is a cable-free desk device that charges on any Qi pad.

## Split of responsibilities

| Deck | Carries |
|---|---|
| Upper (V1 board) | keys, RGB, encoder, joystick, RP2040, USB-C |
| PowerDeck | Qi receiver, Li-ion cell, charger, ideal-diode power mux, pogo pins, magnets |

The ideal diode lives on the PowerDeck, so the V1 board needs no electrical
change to work standalone. USB power and deck power never fight.

## What V1 needs to be V2-ready (optional)

Only if a PowerDeck is actually built:

- 4 pogo-target pads on the back copper (2x VBUS, 2x GND)
- 4 silk-marked magnet zones

V1 ships standalone as-is; these pads are additive and cost nothing when
unused.

## Status

Paper design. The next step, if pursued, is selecting the Qi receiver module
and battery format, then drawing the PowerDeck board.
