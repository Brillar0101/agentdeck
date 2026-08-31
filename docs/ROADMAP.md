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
- Role packs: Dispatch mode loads a curated layout from a YAML pack file
  (key -> label -> colour -> skill/command). Ships with a Software Engineer
  pack bound to real slash commands (review, tdd, verify, build-fix,
  security-scan, simplify, plan, continue, commit). Packs point at skills
  and slash commands, never long inline prompt strings - skills version and
  improve independently; frozen prompts rot. More packs are just more files
- Pipelines: a pack key can run an ordered sequence of steps (each a
  skill/command pointer plus a pass condition) instead of one action. The
  key row is the progress bar - stages light green as they pass; a failing
  stage goes red, halts the pipeline, and pressing it focuses the failure.
  Examples: PCB release (ERC -> DRC -> gerbers -> BOM stock -> CPL -> tag),
  SWE ship (test -> review -> security -> commit -> push). Pipelines are
  always interruptible - the interrupt key aborts a running pipeline
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

### Companion (the deck as a two-sided device)
- Agent-side API: a local bridge endpoint sessions can call deliberately -
  `signal(urgency)` (steady / slow pulse / urgent flash - "FYI" vs "need a
  decision" vs "about to do something hard to reverse"), `ask(options)`
  (pose a question that lights two keys; the pressed key is the answer),
  `presence()` (recording / away / active, so an agent batches questions
  instead of blocking while the human is in a meeting)
- Do-not-disturb key: mutes host notifications and flips presence to "away"
  so agents hold non-urgent questions until it is released
- End-of-day key: one press asks Claude for a digest of what every session
  did today - shipped, blocked, awaiting review - as a Markdown note

### Quality bars
- Agent state change to key colour change <= 1 s
- 8 h session without state drift or reconnect
- Bridge crash never disturbs the sessions it watches; deck unplug degrades
  to plain macro-pad mode

Finished when: one full workday supervising 4+ real Claude Code sessions with
at least one permission approved and one runaway agent interrupted from the
deck, without alt-tabbing to check status.

## V2 - wireless platform

Decision (2026-08-30): AgentDeck goes wireless. V2 is a 20-key (4x5)
control surface on the power/radio platform recovered from the deleted V3
design (git history, pre-297fabb): ESP32-S3-WROOM, LiPo + charging,
USB-C + BLE.

Key layout (decided 2026-08-30): fixed system row (interrupt / PTT /
record / mode - never remapped) + 8 agent keys + 8 action keys in a diode
matrix. An action row doubles as the pipeline progress bar. Board grows to
roughly 115 x 95 mm. V1 stays 13 keys as designed; it is the testbed, not
the product surface.

Architecture:
- ESP32-S3-WROOM module (BLE + USB in one chip; module carries modular
  FCC/CE radio certification, which a commercial version inherits)
- Dual-mode: BLE HID + custom GATT for the state protocol; USB-C is
  charger and full wired fallback - plugged in, the cable wins
- Protected 103450-class LiPo (~2000 mAh), power-path charger (BQ24074
  class, run-while-charging), fuel gauge, charge LED, ship mode
- Firmware: the Arduino/C++ port becomes primary (CircuitPython BLE on
  ESP32-S3 is not dependable)
- Bridge grows a BLE transport (bleak) beside HID; every reconnect repaints
  full state so a BLE drop can never leave stale colours
- Stretch only if free: the 0.96" OLED carried by the V3 design survives
  the delta spec (would give the token screen early)

Phases:
- A (wk 1): recover V3 assets to a `v2-wireless` branch, re-verify LCSC
  stock, write the delta spec
- B (wk 2-4): schematic + layout; RF keepout, battery bay in enclosure
- C (wk 4-6): fab + PCBA; firmware port and BLE transport built while
  boards are in transit
- D (wk 6-9): bring-up; measure 8 h battery target and <= 1 s BLE state
  latency; land the v1.1 feature set on this board

Hedge, in parallel, zero schedule cost: fab the finished V1 wired board
(~$60) as the testbed - keys, LEDs, enclosure fit, and the entire bridge
stack validated on real hardware while V2 is still in layout.

Risks: BLE pairing UX; battery heat in an enclosed printed case (protected
cell, vented design, cell away from the LED field); power-path bugs (bench
test the charger standalone); firmware port slower than hoped (wired HID
fallback stays alive from day one).

## Parked (not before V2 ships)

Deliberately not scheduled. Reopening any of these early is a scope change,
not a roadmap step.

- Colour LCD status strip (rate-limit runway, per-session context fill, burn
  rate, session cost) - unless the V2 OLED stretch covers it
- Per-key e-paper labels (e-ink shows the label, RGB shows the state)
- Onboard far-field microphone
- CNC aluminium enclosure
- Cross-agent adapters / plugin SDK
