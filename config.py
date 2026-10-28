# config.py
# -----------------------------------------------------------------------------
# HeartMeter hardware configuration.
#
# Every pin number and I2C address used by the firmware lives here, so there is
# a single place to change if the wiring ever moves. The values below were taken
# directly from the HeartMeter KiCad board netlist.
#
# Pico GPIO wiring (from the PCB):
#   GPIO2  (physical pin 4) -> Buzzer BZ1 (+)
#   GPIO3  (physical pin 5) -> NeoPixel D1 data-in (DIN)
#   GPIO4  (physical pin 6) -> I2C0 SDA (shared: magnetometer, OLED, ANO wheel)
#   GPIO5  (physical pin 7) -> I2C0 SCL (shared: magnetometer, OLED, ANO wheel)
#   3V3    (physical pin 36)-> power for the I2C breakouts
#   VBUS   (physical pin 40)-> power for the NeoPixel / charger
# -----------------------------------------------------------------------------

# --- GPIO pins (BCM/GPIO numbers, not physical pin numbers) ---
PIN_BUZZER = 2        # drives the passive piezo with a PWM square wave
PIN_NEOPIXEL = 3      # single addressable RGB status LED
PIN_I2C_SDA = 4       # I2C0 data
PIN_I2C_SCL = 5       # I2C0 clock

# --- I2C bus settings ---
I2C_ID = 0            # the Pico I2C peripheral that GP4/GP5 belong to (I2C0)
I2C_FREQUENCY = 400_000   # 400 kHz "fast mode" - fine for all three devices

# --- I2C device addresses ---
# These are the 7-bit addresses each breakout answers to on the shared bus.
ADDR_MAGNETOMETER = 0x30   # MMC5603 fixed address
ADDR_OLED = 0x3C           # SSD1306-family OLED (cut trace moves it to 0x3D)
ADDR_ANO_WHEEL = 0x36      # Adafruit ANO / seesaw encoder default address

# --- Display geometry ---
# The Pimoroni 1.12" mono OLED is 128 x 128 pixels.
OLED_WIDTH = 128
OLED_HEIGHT = 128

# --- NeoPixel ---
NEOPIXEL_COUNT = 1         # one on-board status LED
# This LED expects colours in R, G, B order (not the GRB used by 5050 parts).
NEOPIXEL_ORDER_RGB = True

# --- Buzzer ---
BUZZER_FREQUENCY = 4000    # 4 kHz is the PS1240 piezo's loudest (resonant) tone

# --- Behaviour tuning ---
# How often we read the magnetometer, in milliseconds.
SENSOR_PERIOD_MS = 50

# While taking a magnetometer reading we briefly turn the NeoPixel off, because
# its switching current creates a small magnetic field that would disturb the
# measurement. Set this to False to keep the LED on during readings.
BLANK_LED_DURING_READ = True
