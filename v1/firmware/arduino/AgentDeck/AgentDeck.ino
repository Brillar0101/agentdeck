// AgentDeck firmware, Arduino port (RP2040, arduino-pico core).
//
// A control surface for supervising coding agents: six agent keys that show
// each agent's live state in colour, command keys for accept / reject / new
// chat / push-to-talk, a dial for reasoning effort, and a joystick for
// navigation. This is a straight port of the CircuitPython firmware (code.py);
// behaviour, colours, key chords and the host protocol are identical.
//
// Build
// -----
//   Board:      "Raspberry Pi Pico" (or your RP2040 board), arduino-pico core
//               by Earle Philhower  (github.com/earlephilhower/arduino-pico)
//   Tools menu: USB Stack -> "Adafruit TinyUSB"   (needed for HID + Serial)
//   Libraries:  Adafruit NeoPixel
//
// Physical layout (13 keys)
// -------------------------
//     [ DIAL ]   ACCEPT   REJECT    [ JOYSTICK ]
//     AGENT1     AGENT2   AGENT3    AGENT4
//     AGENT5     AGENT6   NEWCHAT   MODEL
//     FN        [ PUSH-TO-TALK ]    MACRO
//
// Host protocol (USB serial, newline-delimited ASCII) - same as code.py
// ---------------------------------------------------------------------
//   ->  "G <slot> <state>"  agent slot 1-6:  idle|think|work|block|done|err|off
//   ->  "A <led> <state>"   raw LED index 0-12, same states
//   ->  "B <r> <g> <b>"     all LEDs one colour   ->  "X"  reset to idle
//   ->  "P"                 ping (answers "P")
//   <-  "K <name> <0|1>"    key event by role name  <-  "E <+1|-1>"  dial
//   <-  "J <U|D|L|R|C> <0|1>"  joystick

#include <Adafruit_TinyUSB.h>
#include <Adafruit_NeoPixel.h>
#include <Keyboard.h>

// ---------------------------------------------------------------- pins
static const uint8_t KEY_PINS[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 20};
static const uint8_t NUM_KEYS   = sizeof(KEY_PINS) / sizeof(KEY_PINS[0]);  // 13
static const uint8_t ENC_A = 12, ENC_B = 13, ENC_SW = 14;
static const uint8_t JOY_PINS[] = {15, 16, 17, 18, 19};
static const uint8_t NUM_JOY    = 5;
static const char*   JOY_NAMES  = "UDLRC";   // verify on hardware; reorder if needed
static const uint8_t PIXEL_PIN  = 21;
static const uint8_t NUM_LEDS   = 13;        // one per key: 0-11 = SW1-SW12, 12 = SW14 (FN)
static const uint8_t AUX_PINS[] = {22, 23, 24};   // link, activity, error

// ---------------------------------------------------------------- roles
// key index -> role. Index 0..11 are SW1..SW12 (and LED 0..11); 12 is SW14.
enum Role {
  ACCEPT, REJECT,
  AGENT1, AGENT2, AGENT3, AGENT4, AGENT5, AGENT6,
  NEWCHAT, MODEL, PTT, MACRO, FN_ROLE
};
static const Role ROLE[NUM_KEYS] = {
  ACCEPT, REJECT,
  AGENT1, AGENT2, AGENT3, AGENT4,
  AGENT5, AGENT6, NEWCHAT, MODEL,
  PTT, MACRO, FN_ROLE
};
static const char* ROLE_NAME[NUM_KEYS] = {
  "ACCEPT", "REJECT",
  "AGENT1", "AGENT2", "AGENT3", "AGENT4",
  "AGENT5", "AGENT6", "NEWCHAT", "MODEL",
  "PTT", "MACRO", "FN"
};
static const int8_t FN_INDEX = 12;

// Ctrl+Alt combos stay clear of normal typing. The final key per role; the host
// just needs to agree. PTT is held for as long as the key is held.
static const uint8_t CK_CTRL = KEY_LEFT_CTRL, CK_ALT = KEY_LEFT_ALT, CK_SHIFT = KEY_LEFT_SHIFT;
static uint8_t roleKey(Role r) {
  switch (r) {
    case ACCEPT:  return KEY_RETURN;
    case REJECT:  return KEY_BACKSPACE;
    case AGENT1:  return '1';
    case AGENT2:  return '2';
    case AGENT3:  return '3';
    case AGENT4:  return '4';
    case AGENT5:  return '5';
    case AGENT6:  return '6';
    case NEWCHAT: return 'n';
    case MODEL:   return 'm';
    case PTT:     return ' ';
    case MACRO:   return 'x';
    default:      return 0;      // FN has no chord (it is the layer modifier)
  }
}
static const uint8_t DIAL_CW = '=', DIAL_CCW = '-', DIAL_PRESS = 't';   // effort up/down, cycle thinking
static uint8_t joyKey(char n) {
  switch (n) { case 'U': return 'i'; case 'D': return 'k';
               case 'L': return 'j'; case 'R': return 'l'; default: return 'o'; }
}

// ---------------------------------------------------------------- colours
struct RGB { uint8_t r, g, b; };
enum StateId { S_IDLE, S_THINK, S_WORK, S_BLOCK, S_DONE, S_ERR, S_OFF, S_COUNT };
static const char* STATE_NAME[S_COUNT] = {"idle", "think", "work", "block", "done", "err", "off"};
static const RGB   STATE_COLOR[S_COUNT] = {
  {3, 2, 6}, {26, 16, 0}, {30, 10, 0}, {34, 0, 0}, {0, 26, 5}, {32, 0, 14}, {0, 0, 0}
};
static RGB roleColor(Role r) {              // non-agent keys get a steady hint colour
  switch (r) {
    case ACCEPT:  return {0, 14, 3};
    case REJECT:  return {16, 0, 0};
    case NEWCHAT: return {0, 8, 14};
    case MODEL:   return {10, 0, 14};
    case PTT:     return {14, 6, 0};
    case MACRO:   return {6, 6, 6};
    case FN_ROLE: return {2, 2, 2};         // dim white at rest; lights up while the layer is held
    default:      return {0, 0, 0};
  }
}
static const RGB FLASH = {44, 44, 44};

static int8_t stateOf(const char* s) {
  for (int i = 0; i < S_COUNT; i++)
    if (strcmp(s, STATE_NAME[i]) == 0) return i;
  return -1;
}
static bool roleIsAgent(Role r) { return r >= AGENT1 && r <= AGENT6; }

// ---------------------------------------------------------------- setup
Adafruit_NeoPixel pixels(NUM_LEDS, PIXEL_PIN, NEO_GRB + NEO_KHZ800);

int8_t agentState[NUM_LEDS];                 // per-LED StateId, host driven
bool   overrideOn[NUM_LEDS];                 // raw colour from "A"/"B" active
RGB    overrideCol[NUM_LEDS];
unsigned long flashUntil[NUM_LEDS];
unsigned long lastRx = 0;
bool   fnHeld = false;

// debounce state for keys, joystick and the encoder switch
struct Btn { bool raw, stable; unsigned long t; };
Btn keyBtn[NUM_KEYS], joyBtn[NUM_JOY], encBtn;
static const unsigned long DEBOUNCE_MS = 5;

// encoder quadrature decode (divisor 4: one step per detent)
static const int8_t QDEC[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};
uint8_t encPrev = 0;
int     encAccum = 0;

char rxbuf[64];
uint8_t rxlen = 0;

void send(const char* msg) { Serial.print(msg); Serial.print('\n'); }

// press Ctrl+Alt (+Shift on the FN layer) + a key, tap or hold
void chord(uint8_t key, bool withShift, bool hold, bool pressed) {
  if (!key) return;
  if (hold) {
    if (pressed) {
      Keyboard.press(CK_CTRL); Keyboard.press(CK_ALT);
      if (withShift) Keyboard.press(CK_SHIFT);
      Keyboard.press(key);
    } else {
      Keyboard.releaseAll();
    }
  } else if (pressed) {
    Keyboard.press(CK_CTRL); Keyboard.press(CK_ALT);
    if (withShift) Keyboard.press(CK_SHIFT);
    Keyboard.press(key);
    Keyboard.releaseAll();
  }
}
void tap(uint8_t key) { chord(key, false, false, true); }

void setup() {
  TinyUSBDevice.setManufacturerDescriptor("AgentDeck");
  TinyUSBDevice.setProductDescriptor("AgentDeck");

  for (uint8_t i = 0; i < NUM_KEYS; i++) pinMode(KEY_PINS[i], INPUT_PULLUP);
  for (uint8_t i = 0; i < NUM_JOY; i++)  pinMode(JOY_PINS[i], INPUT_PULLUP);
  pinMode(ENC_A, INPUT_PULLUP); pinMode(ENC_B, INPUT_PULLUP); pinMode(ENC_SW, INPUT_PULLUP);
  for (uint8_t i = 0; i < 3; i++) { pinMode(AUX_PINS[i], OUTPUT); digitalWrite(AUX_PINS[i], LOW); }

  for (uint8_t i = 0; i < NUM_LEDS; i++) { agentState[i] = S_IDLE; overrideOn[i] = false; flashUntil[i] = 0; }

  Keyboard.begin();
  Serial.begin(115200);
  pixels.begin();
  pixels.setBrightness(255);
  pixels.show();

  encPrev = (digitalRead(ENC_A) ? 2 : 0) | (digitalRead(ENC_B) ? 1 : 0);
}

// ---------------------------------------------------------------- render
static RGB scale(RGB c, float f) {
  auto clamp = [](int v) { return (uint8_t)(v < 0 ? 0 : v > 255 ? 255 : v); };
  return {clamp((int)(c.r * f)), clamp((int)(c.g * f)), clamp((int)(c.b * f))};
}

void render(unsigned long now) {
  float phase = fmodf((now / 1000.0f) * 2.0f, 2.0f);
  float pulse = phase < 1.0f ? phase : 2.0f - phase;
  for (uint8_t i = 0; i < NUM_LEDS; i++) {
    RGB c;
    if (now < flashUntil[i]) {
      c = FLASH;
    } else if (overrideOn[i]) {
      c = overrideCol[i];
    } else {
      Role role = ROLE[i];
      if (roleIsAgent(role)) {
        c = STATE_COLOR[agentState[i]];
        if (agentState[i] == S_THINK)      c = scale(c, 0.25f + 0.75f * pulse);
        else if (agentState[i] == S_BLOCK) c = (pulse > 0.5f) ? c : (RGB){0, 0, 0};   // blink: needs attention
      } else if (role == FN_ROLE) {
        c = fnHeld ? (RGB){30, 30, 30} : roleColor(FN_ROLE);                          // bright while layer active
      } else {
        c = roleColor(role);
        if (fnHeld) c = scale(c, 3.0f);                                               // brighten on FN layer
      }
    }
    pixels.setPixelColor(i, c.r, c.g, c.b);
  }
  pixels.show();
}

// ---------------------------------------------------------------- host RX
void handle(char* line) {
  char* p = strtok(line, " ");
  if (!p) return;
  bool ok = true;
  if (strcmp(p, "G") == 0) {                                // agent slot 1-6
    char* a = strtok(NULL, " "); char* b = strtok(NULL, " ");
    int slot = a ? atoi(a) - 1 : -1; int st = b ? stateOf(b) : -1;
    static const uint8_t AGENT_LED[6] = {2, 3, 4, 5, 6, 7};
    if (slot >= 0 && slot < 6 && st >= 0) { uint8_t led = AGENT_LED[slot]; agentState[led] = st; overrideOn[led] = false; }
    else ok = false;
  } else if (strcmp(p, "A") == 0) {                         // raw LED index
    char* a = strtok(NULL, " "); char* b = strtok(NULL, " ");
    int i = a ? atoi(a) : -1; int st = b ? stateOf(b) : -1;
    if (i >= 0 && i < NUM_LEDS && st >= 0) { agentState[i] = st; overrideOn[i] = false; }
    else ok = false;
  } else if (strcmp(p, "B") == 0) {
    char* r = strtok(NULL, " "); char* g = strtok(NULL, " "); char* b = strtok(NULL, " ");
    if (r && g && b) { RGB c = {(uint8_t)atoi(r), (uint8_t)atoi(g), (uint8_t)atoi(b)};
      for (uint8_t i = 0; i < NUM_LEDS; i++) { overrideOn[i] = true; overrideCol[i] = c; } }
    else ok = false;
  } else if (strcmp(p, "X") == 0) {
    for (uint8_t i = 0; i < NUM_LEDS; i++) { overrideOn[i] = false; agentState[i] = S_IDLE; }
  } else if (strcmp(p, "P") == 0) {
    send("P");
  }
  lastRx = millis();
  digitalWrite(AUX_PINS[1], !digitalRead(AUX_PINS[1]));
  if (!ok) digitalWrite(AUX_PINS[2], HIGH);
}

// ---------------------------------------------------------------- loop
void loop() {
  unsigned long now = millis();

  // keys
  for (uint8_t i = 0; i < NUM_KEYS; i++) {
    bool raw = (digitalRead(KEY_PINS[i]) == LOW);
    if (raw != keyBtn[i].raw) { keyBtn[i].raw = raw; keyBtn[i].t = now; }
    if (now - keyBtn[i].t > DEBOUNCE_MS && raw != keyBtn[i].stable) {
      keyBtn[i].stable = raw;
      Role role = ROLE[i];
      if (role == FN_ROLE) {
        fnHeld = raw;
      } else {
        uint8_t key = roleKey(role);
        bool hold = (role == PTT);
        chord(key, fnHeld, hold, raw);
        if (raw && i < NUM_LEDS) flashUntil[i] = now + 120;
      }
      char msg[24]; snprintf(msg, sizeof(msg), "K %s %d", ROLE_NAME[i], raw ? 1 : 0); send(msg);
    }
  }

  // joystick
  for (uint8_t i = 0; i < NUM_JOY; i++) {
    bool raw = (digitalRead(JOY_PINS[i]) == LOW);
    if (raw != joyBtn[i].raw) { joyBtn[i].raw = raw; joyBtn[i].t = now; }
    if (now - joyBtn[i].t > DEBOUNCE_MS && raw != joyBtn[i].stable) {
      joyBtn[i].stable = raw;
      char name = JOY_NAMES[i];
      if (raw) tap(joyKey(name));
      char msg[16]; snprintf(msg, sizeof(msg), "J %c %d", name, raw ? 1 : 0); send(msg);
    }
  }

  // encoder switch
  {
    bool raw = (digitalRead(ENC_SW) == LOW);
    if (raw != encBtn.raw) { encBtn.raw = raw; encBtn.t = now; }
    if (now - encBtn.t > DEBOUNCE_MS && raw != encBtn.stable) {
      encBtn.stable = raw;
      if (raw) tap(DIAL_PRESS);
    }
  }

  // encoder rotation
  uint8_t cur = (digitalRead(ENC_A) ? 2 : 0) | (digitalRead(ENC_B) ? 1 : 0);
  encAccum += QDEC[(encPrev << 2) | cur];
  encPrev = cur;
  while (encAccum >= 4)  { tap(DIAL_CW);  send("E +1"); encAccum -= 4; }
  while (encAccum <= -4) { tap(DIAL_CCW); send("E -1"); encAccum += 4; }

  // host RX
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (rxlen) { rxbuf[rxlen] = 0; handle(rxbuf); rxlen = 0; }
    } else if (rxlen < sizeof(rxbuf) - 1) {
      rxbuf[rxlen++] = ch;
    }
  }

  digitalWrite(AUX_PINS[0], (now - lastRx) < 5000 ? HIGH : LOW);   // host bridge alive
  render(now);
  delay(5);
}
