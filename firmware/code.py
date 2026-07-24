"""ClaudeMicro firmware (CircuitPython 9.x, RP2040).

A control surface for supervising coding agents: six agent keys that show each
agent's live state in colour, command keys for accept / reject / new chat /
push-to-talk, a dial for reasoning effort, and a joystick for navigation.

Physical layout (13 keys)
-------------------------
    [ DIAL ]   ACCEPT   REJECT    [ JOYSTICK ]
    AGENT1     AGENT2   AGENT3    AGENT4
    AGENT5     AGENT6   NEWCHAT   MODEL
    FN        [ PUSH-TO-TALK ]    MACRO

Hardware map (read off the PCB netlist)
---------------------------------------
SW1..SW12 keys            GP0..GP11
SW14 key (bottom-left)    GP20
EC11 dial A / B / press   GP12 / GP13 / GP14
Joystick U/D/L/R, centre  GP15..GP18, GP19
SK6812 chain (13 LEDs)    GP21   - one per key (SW1..SW12, then SW14)
Aux LEDs link/act/err     GP22 / GP23 / GP24

Host protocol (second USB CDC channel, newline-delimited ASCII)
--------------------------------------------------------------
->  "G <slot> <state>"  agent slot 1-6:  idle|think|work|block|done|err|off
->  "A <led> <state>"   raw LED index 0-12, same states
->  "B <r> <g> <b>"     all LEDs one colour     ->  "X"  reset to idle
->  "P"                 ping (answers "P")
<-  "K <name> <0|1>"    key event by role name  <-  "E <+1|-1>"  dial
<-  "J <U|D|L|R|C> <0|1>"  joystick
"""
import time

import board
import digitalio
import keypad
import neopixel
import rotaryio
import usb_cdc
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# ---------------------------------------------------------------- pins
KEY_PINS = [getattr(board, f"GP{i}") for i in range(12)] + [board.GP20]
ENC_A, ENC_B, ENC_SW = board.GP12, board.GP13, board.GP14
JOY_PINS = [board.GP15, board.GP16, board.GP17, board.GP18, board.GP19]
JOY_NAMES = "UDLRC"          # verify on hardware; reorder if directions feel wrong
PIXEL_PIN = board.GP21
NUM_LEDS = 13               # one per key: LED index 0-11 = SW1-SW12, 12 = SW14 (FN)
AUX_PINS = [board.GP22, board.GP23, board.GP24]      # link, activity, error

# ---------------------------------------------------------------- roles
# key index -> role. Index 0..11 are SW1..SW12 (and LED 0..11); 12 is SW14.
ROLES = ["ACCEPT", "REJECT",                          # top row
         "AGENT1", "AGENT2", "AGENT3", "AGENT4",      # row 2
         "AGENT5", "AGENT6", "NEWCHAT", "MODEL",      # row 3
         "PTT", "MACRO",                              # wide key, bottom right
         "FN"]                                        # SW14, bottom left
AGENT_KEYS = [i for i, r in enumerate(ROLES) if r.startswith("AGENT")]
FN_INDEX = ROLES.index("FN")

CTRL_ALT = (Keycode.CONTROL, Keycode.ALT)
# Ctrl+Alt combos stay clear of normal typing. Edit freely - the host just needs
# to agree. PTT is held down for as long as the key is held.
BINDINGS = {
    "ACCEPT":  CTRL_ALT + (Keycode.ENTER,),
    "REJECT":  CTRL_ALT + (Keycode.BACKSPACE,),
    "AGENT1":  CTRL_ALT + (Keycode.ONE,),
    "AGENT2":  CTRL_ALT + (Keycode.TWO,),
    "AGENT3":  CTRL_ALT + (Keycode.THREE,),
    "AGENT4":  CTRL_ALT + (Keycode.FOUR,),
    "AGENT5":  CTRL_ALT + (Keycode.FIVE,),
    "AGENT6":  CTRL_ALT + (Keycode.SIX,),
    "NEWCHAT": CTRL_ALT + (Keycode.N,),
    "MODEL":   CTRL_ALT + (Keycode.M,),
    "PTT":     CTRL_ALT + (Keycode.SPACE,),
    "MACRO":   CTRL_ALT + (Keycode.X,),
}
HOLD_ROLES = {"PTT"}                       # held, not tapped
# FN layer: same chord plus Shift (e.g. FN+AGENT3 = stop that agent)
FN_EXTRA = (Keycode.SHIFT,)

DIAL_CW = CTRL_ALT + (Keycode.EQUALS,)     # reasoning effort up
DIAL_CCW = CTRL_ALT + (Keycode.MINUS,)     # reasoning effort down
DIAL_PRESS = CTRL_ALT + (Keycode.T,)       # cycle thinking mode
JOY_BIND = {"U": CTRL_ALT + (Keycode.I,), "D": CTRL_ALT + (Keycode.K,),
            "L": CTRL_ALT + (Keycode.J,), "R": CTRL_ALT + (Keycode.L,),
            "C": CTRL_ALT + (Keycode.O,)}

# ---------------------------------------------------------------- colours
STATE_COLORS = {
    "idle":  (3, 2, 6),      # dim violet - agent connected, waiting
    "think": (26, 16, 0),    # amber, pulsing
    "work":  (30, 10, 0),    # orange
    "block": (34, 0, 0),     # red - needs you
    "done":  (0, 26, 5),     # green
    "err":   (32, 0, 14),    # magenta
    "off":   (0, 0, 0),
}
ROLE_COLORS = {              # non-agent keys get a steady hint colour
    "ACCEPT": (0, 14, 3), "REJECT": (16, 0, 0), "NEWCHAT": (0, 8, 14),
    "MODEL": (10, 0, 14), "PTT": (14, 6, 0), "MACRO": (6, 6, 6),
    "FN": (2, 2, 2),         # dim white at rest; lights up while the layer is held
}
FLASH = (44, 44, 44)

# ---------------------------------------------------------------- setup
kbd = Keyboard(usb_hid.devices)
keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)
joy = keypad.Keys(JOY_PINS, value_when_pressed=False, pull=True)
enc = rotaryio.IncrementalEncoder(ENC_A, ENC_B, divisor=4)
enc_sw = keypad.Keys((ENC_SW,), value_when_pressed=False, pull=True)

aux = []
for p in AUX_PINS:
    d = digitalio.DigitalInOut(p)
    d.direction = digitalio.Direction.OUTPUT
    d.value = False
    aux.append(d)

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_LEDS, brightness=1.0, auto_write=False)
link = usb_cdc.data

agent_state = ["idle"] * NUM_LEDS       # per-LED state, host driven
override = {}                           # led -> raw colour from "A"/"B"
flash_until = [0.0] * NUM_LEDS
last_enc = enc.position
last_rx = 0.0
fn_held = False
rxbuf = b""


def send(msg):
    if link:
        try:
            link.write((msg + "\n").encode())
        except Exception:
            pass


def tap(codes):
    kbd.press(*codes)
    kbd.release_all()


def render(now):
    phase = (now * 2.0) % 2.0
    pulse = phase if phase < 1.0 else 2.0 - phase
    for i in range(NUM_LEDS):
        if now < flash_until[i]:
            pixels[i] = FLASH
            continue
        if i in override:
            pixels[i] = override[i]
            continue
        role = ROLES[i]
        if role.startswith("AGENT"):
            c = STATE_COLORS.get(agent_state[i], STATE_COLORS["idle"])
            if agent_state[i] == "think":
                c = tuple(int(v * (0.25 + 0.75 * pulse)) for v in c)
            elif agent_state[i] == "block":
                c = c if pulse > 0.5 else (0, 0, 0)      # blink: needs attention
        elif role == "FN":
            c = (30, 30, 30) if fn_held else ROLE_COLORS["FN"]   # bright while layer active
        else:
            c = ROLE_COLORS.get(role, (0, 0, 0))
            if fn_held:
                c = tuple(min(255, int(v * 3)) for v in c)   # brighten on FN layer
        pixels[i] = c
    pixels.show()


def handle(line):
    global last_rx
    p = line.split()
    if not p:
        return
    try:
        if p[0] == "G" and len(p) == 3:                  # agent slot 1-6
            slot = int(p[1]) - 1
            if 0 <= slot < len(AGENT_KEYS):
                led = AGENT_KEYS[slot]
                agent_state[led] = p[2]
                override.pop(led, None)
        elif p[0] == "A" and len(p) == 3:                # raw LED index
            i = int(p[1])
            if 0 <= i < NUM_LEDS:
                agent_state[i] = p[2]
                override.pop(i, None)
        elif p[0] == "B" and len(p) == 4:
            c = (int(p[1]), int(p[2]), int(p[3]))
            for i in range(NUM_LEDS):
                override[i] = c
        elif p[0] == "X":
            override.clear()
            for i in range(NUM_LEDS):
                agent_state[i] = "idle"
        elif p[0] == "P":
            send("P")
        last_rx = time.monotonic()
        aux[1].value = not aux[1].value
    except (ValueError, IndexError):
        aux[2].value = True


while True:
    now = time.monotonic()

    ev = keys.events.get()
    if ev:
        i = ev.key_number
        role = ROLES[i]
        if role == "FN":
            fn_held = ev.pressed
        else:
            codes = BINDINGS.get(role)
            if codes and fn_held:
                codes = FN_EXTRA + codes
            if codes:
                if role in HOLD_ROLES:
                    kbd.press(*codes) if ev.pressed else kbd.release(*codes)
                elif ev.pressed:
                    tap(codes)
            if ev.pressed and i < NUM_LEDS:
                flash_until[i] = now + 0.12
        send(f"K {role} {1 if ev.pressed else 0}")

    jev = joy.events.get()
    if jev:
        name = JOY_NAMES[jev.key_number]
        if jev.pressed:
            tap(JOY_BIND[name])
        send(f"J {name} {1 if jev.pressed else 0}")

    eev = enc_sw.events.get()
    if eev and eev.pressed:
        tap(DIAL_PRESS)

    pos = enc.position
    while pos > last_enc:
        tap(DIAL_CW)
        send("E +1")
        last_enc += 1
    while pos < last_enc:
        tap(DIAL_CCW)
        send("E -1")
        last_enc -= 1

    if link and link.in_waiting:
        rxbuf += link.read(link.in_waiting)
        while b"\n" in rxbuf:
            line, rxbuf = rxbuf.split(b"\n", 1)
            handle(line.decode().strip())

    aux[0].value = (now - last_rx) < 5.0        # host bridge alive
    render(now)
    time.sleep(0.005)
