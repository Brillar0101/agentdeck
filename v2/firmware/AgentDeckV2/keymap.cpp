#include "keymap.h"

uint8_t currentLayer = 0;

// HID usage IDs (USB HID Usage Tables ch.10)
constexpr uint8_t HID_ESC = 0x29, HID_ENTER = 0x28;
constexpr uint8_t MOD_CTRL = 1, MOD_SHIFT = 2, MOD_ALT = 4;
constexpr uint8_t CA = MOD_CTRL | MOD_ALT;          // V1 chord convention
constexpr uint8_t CAS = CA | MOD_SHIFT;

// System row: keycode 0 = handled in firmware (MODE) or reported to the host
// as a role (INT/PTT/REC/DND) which the bridge acts on. Same in every mode.
#define SYSTEM_ROW \
  {0, 0, "INT"}, {0, 0, "PTT"}, {0, 0, "REC"}, {0, 0, "MODE"}, {0, 0, "DND"}

// Mode 0: Agents (Ctrl+Alt chords, V1 convention: host maps them)
const KeyBinding L0[20] = {
  SYSTEM_ROW,
  {0x1E, CA, "AGENT1"}, {0x1F, CA, "AGENT2"}, {0x20, CA, "AGENT3"},
  {0x21, CA, "AGENT4"}, {0x22, CA, "AGENT5"},
  {0x23, CA, "AGENT6"}, {0x24, CA, "AGENT7"}, {0x25, CA, "AGENT8"},
  {0x04, CA, "ACCEPT"}, {0x05, CA, "REJECT"},
  {0x13, CA, "PLAN"},   {0x17, CA, "TEST"},   {0x15, CA, "REVIEW"},
  {0x06, CAS, "COMMIT"}, {HID_ENTER, 0, "CONTINUE"},
};

// Mode 1: Dispatch - the Software Engineer role pack (docs/ROADMAP.md).
// Roles are pointers into the bridge's pack YAML; keycodes are placeholders.
const KeyBinding L1[20] = {
  SYSTEM_ROW,
  {0, 0, "PACK1"},  {0, 0, "PACK2"},  {0, 0, "PACK3"},  {0, 0, "PACK4"},  {0, 0, "PACK5"},
  {0, 0, "PACK6"},  {0, 0, "PACK7"},  {0, 0, "PACK8"},  {0, 0, "PACK9"},  {0, 0, "PACK10"},
  {0, 0, "PACK11"}, {0, 0, "PACK12"}, {0, 0, "PACK13"}, {0, 0, "PACK14"}, {0, 0, "PACK15"},
};

// Mode 2: Desk - media/utility keys and user macros.
const KeyBinding L2[20] = {
  SYSTEM_ROW,
  {0, 0, "VOLDN"}, {0, 0, "VOLUP"}, {0, 0, "MUTE"}, {HID_ESC, 0, "ESC"}, {0, 0, "DIGEST"},
  {0, 0, "M1"}, {0, 0, "M2"}, {0, 0, "M3"}, {0, 0, "M4"}, {0, 0, "M5"},
  {0, 0, "M6"}, {0, 0, "M7"}, {0, 0, "M8"}, {0, 0, "M9"}, {0, 0, "M10"},
};

#define ROW20(L) \
  { L[0],L[1],L[2],L[3],L[4],L[5],L[6],L[7],L[8],L[9], \
    L[10],L[11],L[12],L[13],L[14],L[15],L[16],L[17],L[18],L[19] }

const KeyBinding KEYMAP[NUM_LAYERS][20] = { ROW20(L0), ROW20(L1), ROW20(L2) };
