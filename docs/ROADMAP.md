# Roadmap

One version at a time. A milestone is not started until the previous one is
finished, and "finished" is defined at the top of each section.

## v1.0 - manufacture and validate (current)

Nothing in this repo has ever run on real hardware. v1.0 is the fab order,
assembly, and bring-up of the V1 board as designed.

Finished when: an assembled board enumerates over USB, the CircuitPython
firmware runs, all 13 keys / encoder / joystick / LEDs work, the Claude Code
hook bridge drives agent-key colours on a real desk for a full workday.

- Order PCBs + parts from the existing `v1/fab/` package (JLCPCB PCBA)
- Assemble, print the enclosure, flash, bring up
- Fix whatever the hardware disagrees with (expect firmware patches; record
  them in the changelog)
- Live with it for a week; collect the annoyance list

## v1.1 - depth release (no copper changes)

Everything here runs on the v1 board as manufactured. Software and firmware
only, so it can be developed in parallel while v1.0 boards are in transit.

The design brief is the Codex Micro backlash inverted: bidirectional control,
a microphone story, Linux support, and integration deep enough that no $50
macro pad could replicate it.

### Bridge (host side)
- Bidirectional control: blocked agent pulses its key; dedicated approve /
  deny keys answer permission prompts from the deck
- Interrupt key: short-press stops the selected agent, long-press stops all
- Focus-on-press: tmux-first (`switch-client` / `select-window` - works on
  X11, Wayland, and over SSH), window-manager raise as fallback only
- Dispatch keys: saved prompts / slash commands bound per-project profile
- Push-to-talk: hold key, speak, release; local transcription to the active
  session (host microphone)
- Meeting capture: record key toggles; solid red while recording (visible to
  everyone at the desk); local Whisper transcription; Claude-structured
  Markdown notes (summary / decisions / action items) to a configured folder
- Token awareness without a screen: a configured key shifts green -> amber ->
  red as the rate-limit window burns; rate-limited state gets its own colour
- Modes (layered layouts, Stream Deck-style): named layouts - Agents /
  Dispatch / Desk - switched by encoder press and auto-switched by context
  (recording flips to Desk). Hard cap of 3 modes. Each mode has its own
  colour theme so the active mode reads at a glance; a host-side HUD overlay
  flashes the current layout for 2 s on mode change (keys have no displays -
  per-key e-paper labels stay parked and are the eventual fix). The
  interrupt key is mode-invariant: it means stop in every mode, always

### Platform
- Linux and macOS both first-class
- Ship `99-agentdeck.rules` udev rule for raw-HID access on Linux
- Bridge stays local-only: no cloud calls, no telemetry

### Quality bars
- Agent state change to key colour change <= 1 s
- 8 h session without state drift or reconnect
- Bridge crash never disturbs the sessions it watches; deck unplug degrades
  to plain macro-pad mode

Finished when: one full workday supervising 4+ real Claude Code sessions with
at least one permission approved and one runaway agent interrupted from the
deck, without alt-tabbing to check status.

## Parked (requires a board respin - not before v1.1 ships)

Deliberately not scheduled. Reopening any of these before v1.1 is done is a
scope change, not a roadmap step.

- Colour LCD status strip (rate-limit runway, per-session context fill, burn
  rate, session cost)
- Per-key e-paper labels (e-ink shows the label, RGB shows the state)
- Onboard far-field microphone
- BLE / battery / wireless anything
- CNC aluminium enclosure
- Cross-agent adapters / plugin SDK
