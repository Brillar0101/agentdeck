#!/usr/bin/env python3
"""AgentDeck host bridge.

Drives the macropad's six agent keys from agent activity, and can read the
pad's key/dial/joystick events back.

    agentdeck_bridge.py demo                  cycle every state on every agent key
    agentdeck_bridge.py agent <1-6> <state>   set one agent slot
    agentdeck_bridge.py all <state>           set all six
    agentdeck_bridge.py watch                 print events coming from the pad
    agentdeck_bridge.py hook <state> [slot]   for Claude Code hooks (reads stdin)
    agentdeck_bridge.py screen <line> <text>  write OLED status line 0-3 (V3 only)

States: idle | think | work | block | done | err | off

Claude Code hooks (~/.claude/settings.json) - one agent slot per project, or
pass a slot number per hook:

    "hooks": {
      "UserPromptSubmit": [{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/agentdeck/host/agentdeck_bridge.py hook think"}]}],
      "PreToolUse":       [{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/agentdeck/host/agentdeck_bridge.py hook work"}]}],
      "Notification":     [{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/agentdeck/host/agentdeck_bridge.py hook block"}]}],
      "Stop":             [{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/agentdeck/host/agentdeck_bridge.py hook done"}]}]
    }

Requires: pip install pyserial
"""
import sys

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pip install pyserial")

STATES = {"idle", "think", "work", "block", "done", "err", "off"}
SLOTS = range(1, 7)


def open_link():
    """Second (data) CDC interface of the pad; console is the first."""
    ports = [p.device for p in list_ports.comports()
             if "AgentDeck" in " ".join(filter(None, (p.manufacturer, p.product, p.description)))
             or "CircuitPython" in " ".join(filter(None, (p.manufacturer, p.product, p.description)))]
    if not ports:
        sys.exit("AgentDeck not found - plugged in and running the firmware?")
    return serial.Serial(sorted(ports)[-1], 115200, timeout=1)


def send(link, msg):
    link.write((msg + "\n").encode())


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]

    if cmd == "hook":
        sys.stdin.read()                       # consume the hook payload
        state = args[1] if len(args) > 1 else "work"
        slot = args[2] if len(args) > 2 else "1"
        send(open_link(), f"G {slot} {state}")
        return

    link = open_link()

    if cmd == "agent" and len(args) == 3 and args[2] in STATES and int(args[1]) in SLOTS:
        send(link, f"G {args[1]} {args[2]}")

    elif cmd == "all" and len(args) == 2 and args[1] in STATES:
        for s in SLOTS:
            send(link, f"G {s} {args[1]}")

    elif cmd == "demo":
        import time
        for state in ("idle", "think", "work", "block", "done", "err"):
            print(state)
            for s in SLOTS:
                send(link, f"G {s} {state}")
            time.sleep(1.5)
        send(link, "X")

    elif cmd == "screen" and len(args) >= 3 and args[1] in ("0", "1", "2", "3"):
        send(link, f"S {args[1]} {' '.join(args[2:])[:21]}")

    elif cmd == "watch":
        print("listening (Ctrl-C to stop)")
        send(link, "P")
        while True:
            line = link.readline().decode(errors="replace").strip()
            if line:
                print(line)

    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
