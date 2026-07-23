"""ClaudeMicro firmware (CircuitPython 9.x, RP2040).

Controls
--------
12 Choc keys (direct-wired, active low)   GP0..GP11   (SW1..SW12)
EC11 rotary encoder                       GP12/GP13, push GP14
5-way joystick (SKQUCAA010)               GP15..GP18 (A..D), centre GP19
Touch sensor (TTP223, digital out)        GP20 (active high)
SK6812MINI-E chain, 12 per-key RGB LEDs   GP21 (via level shifter U4)
3 aux 0603 indicator LEDs                 GP22 (link) GP23 (activity) GP24 (error)

Keymap (defaults - edit KEYMAP/FN_KEYMAP)
-----------------------------------------
Agent keys  C L A U D E   -> F13..F18   (bind these in your tools)
Command     F1 F2 F3 F4   -> F19..F22
GO (wide)                 -> F23
FN                        -> momentary layer (FN + agent key -> Ctrl+Alt+1..6)
Encoder                   -> volume up/down, push = mute
Joystick                  -> arrows, centre = Enter
Touch pad                 -> F24 (e.g. push-to-talk)

Host bridge protocol (second USB CDC channel, newline-delimited ASCII)
----------------------------------------------------------------------
->  "A <i> <state>"   set agent state of key i (0-11):
                      idle|think|work|block|done|err|off
->  "L <i> <r> <g> <b>"  raw color for key i
->  "B <r> <g> <b>"      all keys
->  "X"                  all off / back to idle
->  "P"                  ping (firmware answers "P")
<-  "K <i> <0|1>"     key event      <- "E <+1|-1>"  encoder
<-  "J <U|D|L|R|C> <0|1>" joystick   <- "T <0|1>"    touch
"""
import time

import board
import digitalio
import keypad
import neopixel
import rotaryio
import usb_cdc
import usb_hid
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# ---------------------------------------------------------------- pins
KEY_PINS = [getattr(board, f"GP{i}") for i in range(12)]        # SW1..SW12
ENC_A, ENC_B, ENC_SW = board.GP12, board.GP13, board.GP14
JOY_PINS = [board.GP15, board.GP16, board.GP17, board.GP18, board.GP19]  # A B C D CTR
JOY_NAMES = "UDLRC"      # A=up B=down C=left D=right CTR=centre (verify on hardware)
TOUCH_PIN = board.GP20
PIXEL_PIN = board.GP21
AUX_PINS = [board.GP22, board.GP23, board.GP24]                  # link, activity, error

# LED chain position -> key index. Chain: D1..D6 (SW1..SW6), D10..D15 (SW7..SW12).
LED_ORDER = list(range(12))   # chain pos i lights key i; fix here if hardware differs

# ---------------------------------------------------------------- keymap
FN_KEY = 11                                     # SW12 = FN (momentary layer)
KEYMAP = [Keycode.F13, Keycode.F14, Keycode.F15, Keycode.F16, Keycode.F17,
          Keycode.F18,                                            # C L A U D E
          Keycode.F19, Keycode.F20, Keycode.F21, Keycode.F22,     # F1..F4
          Keycode.F23,                                            # GO
          None]                                                   # FN
FN_KEYMAP = {i: (Keycode.CONTROL, Keycode.ALT, Keycode.ONE + i) for i in range(6)}
JOY_MAP = {"U": Keycode.UP_ARROW, "D": Keycode.DOWN_ARROW,
           "L": Keycode.LEFT_ARROW, "R": Keycode.RIGHT_ARROW, "C": Keycode.ENTER}
TOUCH_KEY = Keycode.F24

STATE_COLORS = {
    "idle":  (4, 2, 8),      # dim purple
    "think": (24, 16, 0),    # amber pulse
    "work":  (28, 10, 0),    # orange
    "block": (32, 0, 0),     # red
    "done":  (0, 24, 4),     # green
    "err":   (32, 0, 12),    # magenta
    "off":   (0, 0, 0),
}
FLASH = (40, 40, 40)         # keypress feedback

# ---------------------------------------------------------------- setup
kbd = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)

keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)
joy = keypad.Keys(JOY_PINS, value_when_pressed=False, pull=True)
enc = rotaryio.IncrementalEncoder(ENC_A, ENC_B, divisor=4)
enc_sw = keypad.Keys((ENC_SW,), value_when_pressed=False, pull=True)

touch = digitalio.DigitalInOut(TOUCH_PIN)
touch.direction = digitalio.Direction.INPUT
touch.pull = digitalio.Pull.DOWN

aux = []
for p in AUX_PINS:
    d = digitalio.DigitalInOut(p)
    d.direction = digitalio.Direction.OUTPUT
    d.value = False
    aux.append(d)

pixels = neopixel.NeoPixel(PIXEL_PIN, 12, brightness=1.0, auto_write=False)
link = usb_cdc.data

agent_state = ["idle"] * 12
flash_until = [0.0] * 12
last_enc = enc.position
last_touch = touch.value
last_link_rx = 0.0
rxbuf = b""


def send(msg):
    if link:
        try:
            link.write((msg + "\n").encode())
        except Exception:
            pass


def render(now):
    phase = (now * 2.0) % 2.0
    pulse = phase if phase < 1.0 else 2.0 - phase
    for i in range(12):
        if now < flash_until[i]:
            c = FLASH
        else:
            c = STATE_COLORS.get(agent_state[i], STATE_COLORS["idle"])
            if agent_state[i] == "think":
                c = tuple(int(v * (0.3 + 0.7 * pulse)) for v in c)
        pixels[LED_ORDER[i]] = c
    pixels.show()


def handle_line(line):
    global last_link_rx
    parts = line.split()
    if not parts:
        return
    try:
        if parts[0] == "A" and len(parts) == 3:
            i = int(parts[1])
            if 0 <= i < 12:
                agent_state[i] = parts[2]
        elif parts[0] == "L" and len(parts) == 5:
            i = int(parts[1])
            if 0 <= i < 12:
                STATE_COLORS[f"raw{i}"] = (int(parts[2]), int(parts[3]), int(parts[4]))
                agent_state[i] = f"raw{i}"
        elif parts[0] == "B" and len(parts) == 4:
            c = (int(parts[1]), int(parts[2]), int(parts[3]))
            for i in range(12):
                STATE_COLORS[f"raw{i}"] = c
                agent_state[i] = f"raw{i}"
        elif parts[0] == "X":
            for i in range(12):
                agent_state[i] = "idle"
        elif parts[0] == "P":
            send("P")
        last_link_rx = time.monotonic()
        aux[1].value = not aux[1].value          # activity blink
    except (ValueError, IndexError):
        aux[2].value = True                      # error LED


fn_held = False
while True:
    now = time.monotonic()

    ev = keys.events.get()
    if ev:
        i = ev.key_number
        if i == FN_KEY:
            fn_held = ev.pressed
        elif ev.pressed:
            flash_until[i] = now + 0.12
            codes = FN_KEYMAP.get(i) if fn_held and i in FN_KEYMAP else None
            if codes:
                kbd.press(*codes)
                kbd.release_all()
            elif KEYMAP[i]:
                kbd.press(KEYMAP[i])
        elif not ev.pressed and KEYMAP[i]:
            kbd.release(KEYMAP[i])
        send(f"K {i} {1 if ev.pressed else 0}")

    jev = joy.events.get()
    if jev:
        name = JOY_NAMES[jev.key_number]
        code = JOY_MAP[name]
        if jev.pressed:
            kbd.press(code)
        else:
            kbd.release(code)
        send(f"J {name} {1 if jev.pressed else 0}")

    eev = enc_sw.events.get()
    if eev and eev.pressed:
        cc.send(ConsumerControlCode.MUTE)

    pos = enc.position
    while pos > last_enc:
        cc.send(ConsumerControlCode.VOLUME_INCREMENT)
        send("E +1")
        last_enc += 1
    while pos < last_enc:
        cc.send(ConsumerControlCode.VOLUME_DECREMENT)
        send("E -1")
        last_enc -= 1

    t = touch.value
    if t != last_touch:
        if t:
            kbd.press(TOUCH_KEY)
        else:
            kbd.release(TOUCH_KEY)
        send(f"T {1 if t else 0}")
        last_touch = t

    if link and link.in_waiting:
        rxbuf += link.read(link.in_waiting)
        while b"\n" in rxbuf:
            line, rxbuf = rxbuf.split(b"\n", 1)
            handle_line(line.decode().strip())

    aux[0].value = (now - last_link_rx) < 5.0    # link LED: host alive recently
    render(now)
    time.sleep(0.01)
