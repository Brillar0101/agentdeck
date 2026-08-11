# AgentDeck firmware, Arduino version

An Arduino/C++ port of the CircuitPython firmware in `../code.py`. It is a
feature-for-feature match: all 13 keys, the encoder, the joystick, the per-key
LED state colours, the FN layer, and the same host serial protocol.

Use whichever you prefer. CircuitPython is quicker to edit on-device (drag a file
onto the CIRCUITPY drive); the Arduino build compiles to a single UF2 and has no
filesystem to manage.

## Build

- **Core:** arduino-pico by Earle Philhower
  (`https://github.com/earlephilhower/arduino-pico`). Add its board manager URL,
  then install "Raspberry Pi Pico/RP2040".
- **Board:** pick your RP2040 board.
- **Tools -> USB Stack:** set to **Adafruit TinyUSB**. This is required so the
  device can be a USB HID keyboard and a serial port at the same time.
- **Library:** install **Adafruit NeoPixel** (Library Manager). The `Keyboard`
  and `Adafruit_TinyUSB` libraries ship with the core.

Open `AgentDeck/AgentDeck.ino`, select the port, and upload. To enter the
bootloader on a fresh board, hold BOOT while plugging in USB.

## One difference from the CircuitPython build

The CircuitPython firmware exposes two USB serial channels (a REPL console plus a
separate data channel). The Arduino build exposes a **single** serial port and
sends the host protocol over it, because there is no REPL to keep clear.

The host bridge (`../../host/agentdeck_bridge.py`) finds the pad by looking for
"AgentDeck" in the USB descriptor, which this sketch sets, so the same bridge
works with either firmware without changes.

## Pin map and protocol

Identical to the CircuitPython version. See the header comment in
`AgentDeck/AgentDeck.ino` and the tables in `../README.md`.
