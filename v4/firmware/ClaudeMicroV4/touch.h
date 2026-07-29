// CST816-class LCD touch controller @0x15, polled (no INT pin routed).
#pragma once

void touchPanelBegin();     // probe 0x15; silently disable if absent
void touchPanelPoll();      // ~30 Hz; taps in soft-key band -> "TK <n>"
bool touchPanelPresent();
