# HeartSense firmware

MicroPython firmware for the HeartSense magnetic-field meter (Raspberry Pi Pico).

## What it does
- Reads total magnetic field strength from the MMC5603 magnetometer.
- Shows a smooth, scrollable menu on the 128x128 OLED, driven by the ANO wheel
  (turn to scroll, press to select, left to go back).
- Live field screen: big uT readout, bar, green/red status LED, buzzer alert
  when the field is high.
- Calibrate screen: hard-iron calibration (rotate the device while it samples).
- About screen.

## Files
- `main.py`     - runs on power-up; hardware setup + main menu loop
- `config.py`   - all pin numbers and I2C addresses (from the board netlist)
- `magnetometer.py` - MMC5603 driver, SET/RESET + hard-iron calibration
- `oled.py`     - SH1107 128x128 OLED driver (framebuffer based)
- `ano_wheel.py`- Adafruit ANO seesaw encoder driver (wheel + 5 buttons)
- `outputs.py`  - piezo buzzer (PWM) and NeoPixel status LED
- `ui.py`       - smooth eased-scrolling menu + scaled text drawing
- `screens.py`  - live reading, calibrate and about screens

## Installing
Copy every `.py` file in this folder to the root of the Pico's MicroPython
filesystem (e.g. with Thonny or `mpremote`). `main.py` runs automatically at
power-on.

Requires a MicroPython build with the `neopixel` and `framebuf` modules (the
standard Pico build has both).

## Pin wiring (from the PCB)
| Signal        | Pico pin        |
|---------------|-----------------|
| Buzzer        | GPIO2 (pin 4)   |
| NeoPixel DIN  | GPIO3 (pin 5)   |
| I2C SDA       | GPIO4 (pin 6)   |
| I2C SCL       | GPIO5 (pin 7)   |

All three I2C devices (magnetometer 0x30, OLED 0x3C, ANO wheel 0x36) share the
one bus.

## Notes / things to check on real hardware
- OLED controller is assumed to be SH1107. If the display stays blank or looks
  shifted, the init sequence in `oled.py` may need small tweaks for your exact
  panel.
- The ANO wheel's button-to-pin mapping and seesaw address (0x36) are the
  Adafruit defaults; confirm against your breakout.
- Scaled text rebuilds a small framebuffer per character. If the live screen
  feels slow, pre-render the digits once (noted in `ui.py`).
