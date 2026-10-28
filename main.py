# main.py
# -----------------------------------------------------------------------------
# HeartMeter main program.
#
# On a Raspberry Pi Pico running MicroPython, a file named main.py runs
# automatically at power-on. This file:
#   1. sets up every piece of hardware,
#   2. shows a start-up screen,
#   3. then runs the main menu, which is scrolled with the ANO wheel and whose
#      options open the live reading, calibration and about screens.
# -----------------------------------------------------------------------------

import time
from machine import Pin, I2C

import config
from oled import OLED
from magnetometer import Magnetometer
from ano_wheel import AnoWheel
from outputs import Buzzer, StatusLed
from ui import ScrollMenu, draw_text
import screens


class Hardware:
    # A small container that holds every device, so screens can reach them all
    # through one object instead of many separate globals.
    def __init__(self):
        # One shared I2C bus carries the magnetometer, OLED and wheel.
        self.i2c = I2C(
            config.I2C_ID,
            sda=Pin(config.PIN_I2C_SDA),
            scl=Pin(config.PIN_I2C_SCL),
            freq=config.I2C_FREQUENCY,
        )

        self.display = OLED(
            self.i2c, config.ADDR_OLED,
            config.OLED_WIDTH, config.OLED_HEIGHT,
        )
        self.mag = Magnetometer(self.i2c, config.ADDR_MAGNETOMETER)
        self.wheel = AnoWheel(self.i2c, config.ADDR_ANO_WHEEL)
        self.buzzer = Buzzer(config.PIN_BUZZER)
        self.led = StatusLed(config.PIN_NEOPIXEL, config.NEOPIXEL_COUNT)


def splash(hardware):
    # A brief start-up screen with a quick device self-check.
    d = hardware.display
    d.fill(0)
    draw_text(d, "Heart", 20, 24, scale=4)
    draw_text(d, "Sense", 20, 60, scale=4)
    d.hline(10, 100, d.width - 20, 1)

    # Check which I2C devices answered, and show a tick/cross for the sensor.
    found = hardware.i2c.scan()
    sensor_ok = config.ADDR_MAGNETOMETER in found
    msg = "sensor ok" if sensor_ok else "no sensor!"
    draw_text(d, msg, 10, 110, scale=1)
    d.show()

    hardware.led.set_color(0, 0, 40)
    hardware.buzzer.beep(30)
    time.sleep_ms(1200)
    hardware.led.off()


def main():
    hardware = Hardware()
    splash(hardware)

    # The top-level menu. Each label maps to an action below.
    menu = ScrollMenu(
        hardware.display,
        items=[
            "Live Field",
            "Calibrate",
            "About",
        ],
        title="Menu",
    )

    # Draw once so the screen isn't blank before the first wheel movement.
    menu.draw()

    while True:
        # --- handle wheel rotation (scrolling) ---
        steps = hardware.wheel.get_scroll()
        if steps != 0:
            menu.scroll_by(steps)
            hardware.buzzer.beep(5)   # tiny tick for tactile feedback

        # --- handle button presses (selection) ---
        buttons = hardware.wheel.poll_buttons()
        if "select" in buttons or "right" in buttons:
            choice = menu.current_item()
            hardware.buzzer.beep(30)
            if choice == "Live Field":
                screens.live_reading_screen(hardware)
            elif choice == "Calibrate":
                screens.calibrate_screen(hardware)
            elif choice == "About":
                screens.about_screen(hardware)
            # Redraw the menu immediately when we come back.
            menu.draw()

        # --- animate the menu ---
        # Always redraw while the menu is still gliding; once it settles we can
        # ease off to a slower idle redraw to save power.
        menu.draw()
        if menu._is_settled():
            time.sleep_ms(30)
        else:
            time.sleep_ms(8)   # ~120 fps while animating = very smooth


# Running main() inside try/except means that if something goes wrong we show
# the error on the screen instead of failing silently.
try:
    main()
except Exception as error:
    try:
        from machine import Pin, I2C
        import config
        from oled import OLED
        from ui import draw_text
        i2c = I2C(config.I2C_ID, sda=Pin(config.PIN_I2C_SDA),
                  scl=Pin(config.PIN_I2C_SCL), freq=config.I2C_FREQUENCY)
        d = OLED(i2c, config.ADDR_OLED, config.OLED_WIDTH, config.OLED_HEIGHT)
        d.fill(0)
        draw_text(d, "ERROR", 4, 6, scale=2)
        draw_text(d, str(error)[:18], 2, 40, scale=1)
        d.show()
    except Exception:
        pass
    raise
