#!/usr/bin/env python3
"""ClaudeMicro host bridge.

Maps Claude Code (or any agent CLI) activity onto the macropad's per-key RGB
via the board's second USB CDC channel.

Usage:
    claude_bridge.py demo                    # cycle all states (smoke test)
    claude_bridge.py set <key 0-11> <state>  # idle|think|work|block|done|err|off
    claude_bridge.py all <state>
    claude_bridge.py hook <state> [key]      # for Claude Code hooks; reads and
                                             # discards hook JSON on stdin,
                                             # default key = 0

Claude Code hooks example (~/.claude/settings.json):
    "hooks": {
      "PreToolUse":  [{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/claude-micro/host/claude_bridge.py hook work"}]}],
      "Notification":[{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/claude-micro/host/claude_bridge.py hook block"}]}],
      "Stop":        [{"hooks": [{"type": "command",
        "command": "python3 ~/kicad-projects/claude-micro/host/claude_bridge.py hook done"}]}]
    }

Requires: pip install pyserial
"""
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pip install pyserial")

STATES = {"idle", "think", "work", "block", "done", "err", "off"}


def find_port():
    """Second (data) CDC interface of the ClaudeMicro board."""
    candidates = []
    for p in list_ports.comports():
        text = " ".join(filter(None, (p.manufacturer, p.product, p.description)))
        if "ClaudeMicro" in text or "CircuitPython" in text:
            candidates.append(p.device)
    if not candidates:
        sys.exit("ClaudeMicro not found. Is it plugged in and running the firmware?")
    # CircuitPython exposes console first, data second; pick the highest-numbered
    return sorted(candidates)[-1]


def open_link():
    return serial.Serial(find_port(), 115200, timeout=1)


def send(link, msg):
    link.write((msg + "\n").encode())


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]

    if cmd == "hook":
        sys.stdin.read()                     # consume hook JSON payload
        state = args[1] if len(args) > 1 else "work"
        key = args[2] if len(args) > 2 else "0"
        link = open_link()
        send(link, f"A {key} {state}")
        return

    link = open_link()
    if cmd == "set" and len(args) == 3 and args[2] in STATES:
        send(link, f"A {args[1]} {args[2]}")
    elif cmd == "all" and len(args) == 2 and args[1] in STATES:
        for i in range(12):
            send(link, f"A {i} {args[1]}")
    elif cmd == "demo":
        for state in ("idle", "think", "work", "block", "done", "err"):
            print(state)
            for i in range(12):
                send(link, f"A {i} {state}")
            time.sleep(1.2)
        send(link, "X")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
