#include "keymap.h"

uint8_t currentLayer = 0;

// HID usage IDs (USB HID Usage Tables ch.10)
#define K(c) (c)
constexpr uint8_t HID_A = 0x04, HID_ESC = 0x29, HID_ENTER = 0x28;
constexpr uint8_t HID_UP = 0x52, HID_DOWN = 0x51, HID_LEFT = 0x50, HID_RIGHT = 0x4F;
constexpr uint8_t MOD_CTRL = 1, MOD_SHIFT = 2, MOD_ALT = 4;
constexpr uint8_t CA = MOD_CTRL | MOD_ALT;          // V1 chord convention
constexpr uint8_t CAS = CA | MOD_SHIFT;

// Layer 0: Claude Code (Ctrl+Alt chords, V1 convention: host maps them)
const KeyBinding L0[24] = {
  {K(0x04), CA, "ACCEPT"}, {K(0x05), CA, "REJECT"}, {K(0x13), CA, "PLAN"},
  {K(0x05), CAS, "BUILD"}, {K(0x17), CA, "TEST"},   {K(0x06), CAS, "COMMIT"},
  {K(0x1E), CA, "AGENT1"}, {K(0x1F), CA, "AGENT2"}, {K(0x20), CA, "AGENT3"},
  {K(0x21), CA, "AGENT4"}, {K(0x22), CA, "AGENT5"}, {K(0x23), CA, "AGENT6"},
  {K(0x11), CA, "NEWCHAT"},{K(0x10), CA, "MODEL"},  {K(0x06), CA, "COMPACT"},
  {HID_ESC, 0, "ESC"},     {HID_UP, 0, "UP"},       {0, 0, "PTTLOCK"},
  {0, 0, "LAYER-"},        {0, 0, "FN"},            {HID_LEFT, 0, "LEFT"},
  {HID_DOWN, 0, "DOWN"},   {HID_RIGHT, 0, "RIGHT"}, {0, 0, "LAYER+"},
};

// Layer 1: browser/media; Layer 2: user macros (host-defined via P protocol)
const KeyBinding L1[24] = {
  {0x3A,0,"F1"},{0x3B,0,"F2"},{0x3C,0,"F3"},{0x3D,0,"F4"},{0x3E,0,"F5"},{0x3F,0,"F6"},
  {0x40,0,"F7"},{0x41,0,"F8"},{0x42,0,"F9"},{0x43,0,"F10"},{0x44,0,"F11"},{0x45,0,"F12"},
  {0,0,"VOLDN"},{0,0,"VOLUP"},{0,0,"MUTE"},{HID_ESC,0,"ESC"},{HID_UP,0,"UP"},{0,0,"PTTLOCK"},
  {0,0,"LAYER-"},{0,0,"FN"},{HID_LEFT,0,"LEFT"},{HID_DOWN,0,"DOWN"},{HID_RIGHT,0,"RIGHT"},{0,0,"LAYER+"},
};
const KeyBinding L2[24] = {
  {0,0,"M1"},{0,0,"M2"},{0,0,"M3"},{0,0,"M4"},{0,0,"M5"},{0,0,"M6"},
  {0,0,"M7"},{0,0,"M8"},{0,0,"M9"},{0,0,"M10"},{0,0,"M11"},{0,0,"M12"},
  {0,0,"M13"},{0,0,"M14"},{0,0,"M15"},{HID_ESC,0,"ESC"},{HID_UP,0,"UP"},{0,0,"PTTLOCK"},
  {0,0,"LAYER-"},{0,0,"FN"},{HID_LEFT,0,"LEFT"},{HID_DOWN,0,"DOWN"},{HID_RIGHT,0,"RIGHT"},{0,0,"LAYER+"},
};

const KeyBinding KEYMAP[NUM_LAYERS][24] = {
  { L0[0],L0[1],L0[2],L0[3],L0[4],L0[5],L0[6],L0[7],L0[8],L0[9],L0[10],L0[11],
    L0[12],L0[13],L0[14],L0[15],L0[16],L0[17],L0[18],L0[19],L0[20],L0[21],L0[22],L0[23] },
  { L1[0],L1[1],L1[2],L1[3],L1[4],L1[5],L1[6],L1[7],L1[8],L1[9],L1[10],L1[11],
    L1[12],L1[13],L1[14],L1[15],L1[16],L1[17],L1[18],L1[19],L1[20],L1[21],L1[22],L1[23] },
  { L2[0],L2[1],L2[2],L2[3],L2[4],L2[5],L2[6],L2[7],L2[8],L2[9],L2[10],L2[11],
    L2[12],L2[13],L2[14],L2[15],L2[16],L2[17],L2[18],L2[19],L2[20],L2[21],L2[22],L2[23] },
};
