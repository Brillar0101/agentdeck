# ClaudeMicro V3 firmware

Arduino (ESP32-S3), dual-transport HID: USB when plugged, BLE ("ClaudeMicroV3")
when on battery. Host protocol is V1's CDC protocol plus `S <line> <text>` for
the OLED. See `docs/DESIGN-V3.md` for architecture; `pins.h` mirrors the
generator's PINOUT table (diff them after any hardware change).

## Build

```
arduino-cli compile --fqbn esp32:esp32:esp32s3 v3/firmware/ClaudeMicroV3
arduino-cli upload  --fqbn esp32:esp32:esp32s3 -p /dev/tty.usbmodem* ...
```
Libraries: Adafruit NeoPixel, U8g2, NimBLE-Arduino.

First flash of a blank board: hold BOOT, tap RESET, release BOOT, then upload
(native USB). After the first flash, auto-reset works.

## Verify on first hardware (V1 tradition)

- [ ] Matrix orientation: ROW/COL vs physical grid (press K1, check index 0)
- [ ] Diode direction = COL2ROW assumed by scan (rows driven low)
- [ ] LED chain order vs key numbering; GRB color order
- [ ] Touch threshold: log `touchRead(PIN_TOUCH)` idle vs pressed, set margin
- [ ] VBAT ADC calibration against multimeter at full/half charge
- [ ] CHRG/STDBY polarity from TP4056 while charging
- [ ] BLE pairing from macOS; auto-switch on USB unplug
- [ ] OLED address (0x3C vs 0x3D)
