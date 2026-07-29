# ClaudeMicro V4 firmware

Arduino (ESP32-S3), dual-transport HID: USB when plugged, BLE ("ClaudeMicroV4")
when on battery. V3 base plus I2S voice (MEMS mic + NS4168 amp), ST7789
240x280 touch LCD (replaces the OLED), and a second EC11. Host protocol is
V3's CDC protocol plus `N <freq> <ms>` (beep), `R` (mic RMS reply) inbound and
`F`/`FS` (ENC2), `TK <n>` (soft-key tap), `W 1` (wake word) outbound - all
additive, so `claude_bridge.py` needs no change (it matches the "ClaudeMicro"
name substring). See `docs/DESIGN-V4.md` for architecture; `pins.h` mirrors
the generator's PINOUT table (diff them after any hardware change).

## Build (verified)

```
arduino-cli compile --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=enabled" v4/firmware/ClaudeMicroV4
arduino-cli upload  --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=8M,PSRAM=enabled" -p /dev/tty.usbmodem* v4/firmware/ClaudeMicroV4
```
Libraries: Adafruit NeoPixel, Adafruit GFX Library, "Adafruit ST7735 and
ST7789 Library", NimBLE-Arduino. ESP_I2S ships with the esp32 core (3.x).

First flash of a blank board: hold BOOT, tap RESET, release BOOT, then upload
(native USB). After the first flash, auto-reset works.

## Wake word (compiled out by default - honest status)

`ESP_SR` (WakeNet9 "Hi ESP" + MultiNet + flite) links ~3 MB and overflows the
1.25 MB app partition of the default 8 MB scheme above; the core's only stock
SR partition scheme (`esp_sr_16`) is 16 MB. Until a custom 8 MB partition
table (>=3 MB app + `model` partition, `srmodels.bin` flashed at its offset)
is added, voice is **PTT-only** (touch pad) and boot prints
`# audio: wake word compiled out (CLAUDEMICRO_WAKEWORD=0), PTT-only voice`.
To experiment: set `CLAUDEMICRO_WAKEWORD` to 1 in `audio.cpp`; the code then
probes for the `model` partition at runtime and degrades to PTT-only if it is
missing. Custom "hey Claude" model = Espressif model training, TODO.

## Verify on first hardware (V1 tradition)

- [ ] Matrix orientation: ROW/COL vs physical grid (press K1, check index 0)
- [ ] Diode direction = COL2ROW assumed by scan (rows driven low)
- [ ] LED chain order vs key numbering; GRB color order
- [ ] Touch pad threshold: log `touchRead(PIN_TOUCH)` idle vs pressed
- [ ] VBAT ADC calibration against multimeter at full/half charge
- [ ] BLE pairing from macOS; auto-switch on USB unplug
- [ ] ENC2 direction and switch polarity (`F`/`FS` events on CDC)

LCD:
- [ ] Row offset: `init(240, 280)` applies the 240x280 offset of 20 - confirm
      no 20 px garbage band top/bottom; adjust rotation if the connector ends
      up on the wrong edge
- [ ] Touch presence: boot with the touch module fitted, tap the bottom
      soft-key band, expect `TK 1..4`; a non-touch panel variant must stay
      silent (no ACK at 0x15 -> polled reads disabled)

Audio:
- [ ] Mic sanity: send `R` over CDC, expect `R <rms>` (>0 idle noise floor,
      clearly larger when speaking); only valid while wake word is off
- [ ] Amp beep: send `N 880 200`, expect a clean 880 Hz tone - NS4168
      CTRL=VDD must pick the right slot (mono is duplicated to both)
- [ ] Wake word smoke test (only with the custom partition build): say
      "Hi ESP", expect `W 1` on CDC + violet LED flash
