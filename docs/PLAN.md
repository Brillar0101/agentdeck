# Claude Micro — plan (no build yet)

> A desk controller for Claude Code, in the spirit of the Work Louder x OpenAI
> Codex Micro. Planning document only. Nothing here is committed to hardware.

## 1. What the Codex Micro is (research summary)

$230 limited-run macropad by Work Louder with OpenAI, launched 2026-07-15,
based on Work Louder's Creator Micro 2. Sources:
- Product page: https://worklouder.cc/codex-micro
- Tom's Hardware: https://www.tomshardware.com/peripherals/keyboards/openais-first-hardware-device-is-an-rgb-macropod-codex-micro-features-13-low-profile-keys-and-a-joystick-for-controlling-ai-coding-agents
- The New Stack: https://thenewstack.io/openai-codex-micro-macropad/
- OpenAI collab page: https://openai.com/supply/co-lab/work-louder/

Spec as reported: 13 mechanical switches, 1 rotary encoder, 1 planar
joystick, 1 touch sensor, 6 programmable layers, USB-C + Bluetooth,
Mac/Windows, aluminum base + sandblasted unibody polycarbonate frame,
PBT/PC caps (32 icon + 11 solid), POM/POK switches, RGB.

## 2. Layout observed from product photos (reference/ folder)

Front face, top to bottom:

| Row | Contents |
|---|---|
| 1 | rotary dial (two-tone cap) · 2 frosted RGB agent keys · 4-way joystick (black, dashed silk outline) |
| 2 | 4 frosted RGB agent keys |
| 3 | 4 white icon keys: lightning, accept (check), reject (x), branch (arrow) |
| 4 | touch dot (black, capless) + 3 tiny aux status LEDs · wide mic bar (~2u) · cloud-face key |

Other observations: up-arrow silk legend top center; edge silk lines
"Work Louder | OpenAI 2026", "You can just build things", "Let's build";
4 hex screws through the frosted top plate; low-profile sculpted caps;
agent-key glow reads through frosted caps very evenly (diffusion is a
quality bar to match).

Default functions (reported + inferred):
- 6 agent keys = live thread status lamps (white idle / blue thinking /
  green done / amber needs input / red error); press to focus that thread;
  configurable to pinned / recent / needs-attention.
- Icon keys: accept changes, reject changes, branch thread, quick action.
- Mic bar: push-to-talk into the composer. Cloud key: ask/explain (inferred).
- Dial: scroll + select (press = confirm). Joystick: composer/UI navigation.
- Touch dot: undocumented (likely layer/wake). 6 layers over everything.

## 3. Claude Micro concept

The pitch: the six lamps answer "which of my Claude sessions needs me?"
without alt-tabbing. Claude Code is better suited than Codex here because
hooks give us every state transition natively.

### Proposed default mapping

| Control | Claude Code action |
|---|---|
| Agent key 1-6 | one Claude Code session each; LED = state; press = focus its terminal window/tmux pane |
| LED states | orange #D97757 working · white idle · amber waiting-on-permission · green done · red error · blue thinking/planning |
| Accept key | approve current permission prompt (send "y"/Enter) |
| Reject key | deny prompt (Esc) |
| Branch key | new session in current repo |
| Lightning | /compact or a user macro |
| Mic bar | hold-to-dictate (host OS dictation into the focused composer) |
| Cloud/face key | toggle plan mode (Shift+Tab) |
| Dial | scroll transcript; press = Enter |
| Joystick | pane/window navigation |
| Touch dot | acknowledge/silence notifications |

### Host integration architecture

```
Claude Code hooks (SessionStart/Stop/Notification/PreToolUse...)
        v  (hook scripts POST state)
local daemon (menu-bar or CLI; owns session<->key assignment)
        v  raw HID reports (LED states)          ^ key events
Claude Micro over USB                    terminal automation
                                 (focus window, send keys, tmux targets)
```

The daemon is the real product. The pad is a QMK device with raw HID.

## 4. Hardware architecture (options, recommendation, NOT final)

| Block | Recommended v1 | Alternatives | Why |
|---|---|---|---|
| MCU | RP2040 + QMK, USB-C only | nRF52840+ZMK (adds BT, but host->LED path is hard in ZMK); ESP32-S3 custom fw (BT+USB, most code) | QMK raw HID is proven; wireless deferred to v2 |
| Switches | Kailh Choc v1, hotswap sockets | Choc v2, Gateron LP | low profile like the original, huge cap ecosystem |
| Per-key RGB | SK6812 MINI-E x6 (agent keys) | full RGB all keys | MINI-E mounts through-plate for clean underglow-through-frost |
| Encoder | EC11 with push | -- | commodity |
| Joystick | 5-way tact (SKQUCAA-style) | PSP analog thumbstick (needs ADC + QMK pointing device) | photos show a digital 4-way rocker; digital is simpler |
| Touch | TTP223 cap-touch IC + PCB pad | MPR121 | RP2040 has no native touch |
| Aux LEDs | 3x 0603 side LEDs | -- | match the original's status trio |
| Enclosure | 3D-printed translucent resin/PETG frame + weighted printed base | CNC polycarbonate + alu (quote later; this is where the $230 goes) | print first, CNC when happy |
| Caps | MBK Choc blanks; frosted/translucent caps for the 6 agent keys; UV-printed legends | relegendable Choc caps | frosted low-profile caps are the main sourcing risk |

Draft cost target: $45-70 in parts DIY (PCB+PCBA ~$25-35, switches/caps
~$15, enclosure print ~$10) vs $230 retail. CNC enclosure would add ~$60+.

## 5. Phases and decision gates

1. **Spec freeze** (needs decisions below)
2. Schematic + layout, script-generated like NeuralCard (same pipeline:
   generator scripts, freerouting, JLCPCB assembly)
3. QMK firmware: keymap, raw HID protocol, LED driver
4. Host daemon: hook scripts + session registry + HID bridge + terminal
   automation (tmux first, then window focus on macOS)
5. Enclosure CAD + print; keycap legends
6. v2 candidates: Bluetooth (nRF52840), haptics, OLED

### Decisions needed before anything gets built

- Wireless in v1, or USB-C only? (recommend USB-only)
- tmux-based session switching or macOS window focus? (recommend tmux)
- Same 4x4-ish footprint as the original, or bigger caps/grid?
- Budget ceiling, and print vs CNC for the enclosure?
- Naming: "Claude" is Anthropic's trademark. Fine as a personal project;
  don't sell it under that name. Consider "Crail Micro" (the brand orange)
  if it ever goes public.

## 6. Risks and open questions

- Frosted-cap light diffusion quality is the whole look; needs cap samples.
- Exact device dimensions unknown (est. ~90x90mm from Choc pitch in photos;
  measure when possible).
- Permission-prompt automation must respect that some prompts SHOULD be
  read; accept-key blindly sending "y" is a footgun. Daemon should only
  ack prompts it can classify.
- Voice key depends on host OS dictation; scope carefully.
- Work Louder's Input software is proprietary; nothing from it is used or
  copied. Clean-room: commodity parts + QMK + our own daemon.

## 7. Prior art: pi-codex-micro (major input)

https://github.com/jal-co/pi-codex-micro (cloned in reference/, no license
file — treat as read-only study material, don't copy code until licensed).
A TypeScript extension wiring the real Codex Micro to the pi coding agent.
What it teaches us:

1. **The input side needs no custom protocol.** They drive everything by
   mapping the Micro's controls to plain keystrokes (enter, escape,
   ctrl+alt+X chords) that the agent's own keybindings catch. Our daemon
   can start the same way with Claude Code keybindings, and raw HID is
   only needed for the LED direction.
2. **Simulator-first works.** Their `/codex-micro sim` is a browser-based
   virtual device where every running agent session occupies an agent key
   with live state, no hardware needed. We should build the Claude Micro
   as software first: same daemon, same protocol, virtual device in a
   browser. Hardware then just replaces the mock transport.
3. **Expected HID shape of Work Louder hardware** (their protocol notes):
   QMK-style interfaces — keyboard 0x0001/0x0006, consumer 0x000C/0x0001,
   and VIA raw HID at usage page 0xFF60 usage 0x0061. Our clone should
   expose exactly this, which makes their extension trivially portable to
   our hardware later.
4. **Terminal-agnostic pane jumping matrix**: detect Zentty via
   ZENTTY_PANE_ID, tmux via TMUX_PANE, WezTerm via WEZTERM_PANE, Kitty via
   KITTY_WINDOW_ID; each session runs its own focus command. Adopt this
   design directly in our daemon.
5. **The real Codex Micro's LED protocol is undocumented** — they ship a
   mock transport waiting on reverse engineering. Our clone's advantage:
   we own the firmware, so our LED protocol is open by construction.

Plan change this implies: insert a phase 0 before hardware — build the
daemon + browser simulator against Claude Code hooks. It validates the
whole UX for zero dollars and becomes the host software the hardware needs
anyway.

## 8. Reference material collected

- reference/codex-micro-og.png (press hero, 1920x1080)
- reference/codex-micro-1..4.webp (product gallery, 2048px)
- Two user-supplied screenshots (front views, key glow states) described
  in section 2.

Still wanted: side/rear/underside photos, Creator Micro 2 teardown links,
exact dimensions, Input app screenshots for daemon UX reference.

## 9. What users complain about, and what we do differently

Sources: Work Louder's public feedback board (feedback.worklouder.cc),
HN thread on the launch (news.ycombinator.com/item?id=48923079, 92
comments), TechRadar's reaction roundup, Reddit quotes therein. The Codex
Micro itself is days old, so platform complaints come from the Creator
Micro 2 / Nomad line it's built on.

### Platform complaints (feedback board, documented bugs)

| Complaint | Evidence | Claude Micro response |
|---|---|---|
| Input app fails to detect devices (Mac M-series, several products) | multiple board posts | No proprietary configurator. QMK + standard VIA protocol; any VIA client works; config lives in a text file |
| Firmware updates break older devices, no graceful recovery | "please handle old firmware versions" post | RP2040 UF2 bootloader: hold BOOTSEL, drag a file. Unbrickable by construction |
| BT mode traps: device stays in Bluetooth when unplugged, 3-tap cycling confusion, no USB-only preference | Creator Micro V2 post | v1 is USB-only. Wireless deferred until it can be done without mode traps |
| Battery life 3 days actual vs 50 advertised | feedback board bug | No battery in v1; nothing to overpromise |
| Preset installs fail, configuration is tedious | Figma preset posts | Presets are text files in a git repo |
| Macro reliability concerns | feedback board | QMK macros are mature; daemon-side macros are scriptable and testable |

### Market reaction to the Codex Micro concept (HN/Reddit)

| Criticism | Representative take | Claude Micro response |
|---|---|---|
| Price: "$230 for 12 keys feels like a prank" | Reddit via TechRadar | DIY target $45-70; that IS the project |
| "Why is a physical object better than a window on screen?" | HN top-voted skepticism | Honest answer: glanceable ambient status + eyes-stay-on-code muscle memory. And phase 0 ships the window version (the simulator) so the hardware is an optional tier, not a gate |
| "Stream Deck is cheaper and has per-key screens" | HN | Acknowledge. Daemon abstracts the display backend, so a Stream Deck frontend can be a supported alternative later; our hardware differentiates on tactile keys, dial, per-key status semantics |
| Codex lock-in / single-vendor toy | HN | Open hardware + open protocol; daemon targets Claude Code first but state model (idle/working/needs-input/done/error) is agent-agnostic |
| Novelty that tests OpenAI hardware ops, not a tool | HN | Ship the daemon as genuinely useful software; hardware earns its place or the sim suffices |

An HN commenter also linked a r/ClaudeCode post titled "I built..." that
appears to be a DIY Claude equivalent already — locate that thread and
study it before phase 0 (open item).

Net effect on the plan: the differentiators are now explicit
requirements — text-file config, UF2 recovery, USB-first, simulator as a
first-class product, open LED protocol.

## 10. What the Claude Code community already built, and what's missing

In June 2026, r/ClaudeCode and X had a wave of DIY status-light projects
wired to Claude Code hooks (per XDA's coverage and the repos below). The
demand for ambient agent status is proven. Every existing solution covers
only half the loop:

| Existing project | What it does | What it lacks |
|---|---|---|
| claude-lamp (bobek-balinek) | Moonside BLE lamps: navy working, mango idle, purple needs input | one lamp = one session; macOS-only BLE; vendor-locked lamp; output only |
| agent-light (eternityspring) | Claude Code status light system | output only |
| mini traffic lights on monitors (the June wave) | red/amber/green per hook events | one session; output only |
| $5 smart bulb hack | amber thinking, green done | one session; output only; smart-home latency |
| Rust/eframe floating traffic light | virtual, no hardware | one session; screen real estate; output only |
| sound/ntfy notification hooks | ding on Stop/Notification | interrupt-driven, not glanceable; no way to act |
| CodeAgentSwarm | terminal manager with per-terminal color status | software only, its own terminal; no physical control |

The two structural gaps, which are exactly the Codex Micro's thesis and
this project's requirements:

1. **Everything is output-only.** A lamp tells you Claude needs input;
   you still alt-tab, find the pane, read, type. No existing project has
   the input half: press the session's key to focus it, accept/reject
   from the same hand.
2. **Everything is single-session.** The people building these are the
   multi-session crowd, yet no solution shows N sessions at once. Six
   per-session lamps is the actual unmet need.

Also worth stealing while designing the daemon: claude-lamp's hook
integration and color language (navy/mango/purple has real-world testing),
and the floating-window traffic light validates the phase-0 simulator as
a product people want even without hardware. Study repos before phase 0:
github.com/bobek-balinek/claude-lamp, github.com/eternityspring/agent-light.
