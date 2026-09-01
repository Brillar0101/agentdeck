// V2 keymap: 20 keys (4x5) x 3 modes. Row 0 is the fixed system row and is
// identical in every mode (docs/ROADMAP.md: interrupt is mode-invariant).
#pragma once
#include <stdint.h>

struct KeyBinding {
  uint8_t keycode;   // HID usage (0 = special role handled in firmware/host)
  uint8_t mods;      // modifier bitmask (Ctrl=1, Shift=2, Alt=4, Gui=8)
  const char *role;  // for host protocol + OLED legend
};

constexpr int NUM_LAYERS = 3;      // modes: 0 Agents, 1 Dispatch, 2 Desk
extern uint8_t currentLayer;
extern const KeyBinding KEYMAP[NUM_LAYERS][20];

// Physical layout (row-major, index = row*5 + col):
//  row0  INT    PTT    REC    MODE   DND        <- system row, every mode
//  row1  AGENT1 AGENT2 AGENT3 AGENT4 AGENT5     <- mode 0 (Agents)
//  row2  AGENT6 AGENT7 AGENT8 ACCEPT REJECT
//  row3  PLAN   TEST   REVIEW COMMIT CONTINUE
// Modes 1/2 keep the system row and rebind rows 1-3 (see keymap.cpp).
