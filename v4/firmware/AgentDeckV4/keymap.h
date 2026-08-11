// V4 keymap: 24 keys x layers - unchanged from V3 (AI-workflow roles).
#pragma once
#include <stdint.h>

struct KeyBinding {
  uint8_t keycode;   // HID usage
  uint8_t mods;      // modifier bitmask (Ctrl=1, Shift=2, Alt=4, Gui=8)
  const char *role;  // for host protocol + LCD legend
};

constexpr int NUM_LAYERS = 3;
extern uint8_t currentLayer;
extern const KeyBinding KEYMAP[NUM_LAYERS][24];

// Roles, layer 0 (Claude Code):
//  ACCEPT REJECT PLAN   BUILD  TEST   COMMIT
//  AGENT1 AGENT2 AGENT3 AGENT4 AGENT5 AGENT6
//  NEWCHAT MODEL COMPACT ESC   UP     PTT-LOCK
//  LAYER-  FN    LEFT   DOWN  RIGHT  LAYER+
// Layers 1/2: browser/media and user macros - defined in keymap.cpp.
//
// V4 encoders (host events, additive to V3's E <+-1> on ENC1):
//  ENC2 rotation emits "F <+-1>" (volume/PTT gain at the host's discretion),
//  ENC2 switch emits "FS <0|1>". Keys themselves are untouched from V3.
