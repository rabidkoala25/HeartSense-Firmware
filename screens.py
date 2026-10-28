# screens.py
# -----------------------------------------------------------------------------
# The individual screens the device can show, other than the main menu.
#
# Each screen is a small function that runs its own little loop: it reads input,
# draws itself, and returns when the user backs out (usually by pressing the
# "left" direction on the wheel, or centre to confirm).
#
# These are deliberately simple and self-contained so they are easy to read and
# change one at a time.
# -----------------------------------------------------------------------------

import time

import config
from ui import draw_text, text_width


# A warning threshold, in microtesla. Above this, the device flags the field as
# "high". Earth's field is roughly 50 uT, so this leaves clear headroom.
DEFAULT_WARN_THRESHOLD = 150.0


def _read_strength_blanked(hardware):
    # Reads field strength, briefly turning the status LED off during the
    # measurement if that option is enabled (to keep the LED's own magnetic
    # noise out of the reading).
    if config.BLANK_LED_DURING_READ:
        hardware.led.save_and_blank()
        value = hardware.mag.read_strength()
        hardware.led.restore()
    else:
        value = hardware.mag.read_strength()
    return value


def live_reading_screen(hardware, warn_threshold=DEFAULT_WARN_THRESHOLD):
    # Shows the live magnetic field strength as a big number, a bar, and a
    # colour-coded status. The status LED mirrors the state:
    #   green  = normal
    #   red    = above the warning threshold (buzzer beeps too)
    #
    # Exit by pressing the wheel's left direction.
    d = hardware.display
    last_beep = 0

    while True:
        # --- input: leave on "left" ---
        for button in hardware.wheel.poll_buttons():
            if button in ("left", "select"):
                hardware.led.off()
                return

        # --- read the sensor ---
        strength = _read_strength_blanked(hardware)
        over = strength > warn_threshold

        # --- draw ---
        d.fill(0)
        draw_text(d, "FIELD", 4, 4, scale=2)
        d.hline(0, 24, d.width, 1)

        # Big number (microtesla), e.g. "123".
        number = "{:.0f}".format(strength)
        number_scale = 4
        nx = (d.width - text_width(number, number_scale)) // 2
        draw_text(d, number, nx, 44, scale=number_scale)
        # Units underneath.
        units = "uT"
        draw_text(d, units, (d.width - text_width(units, 2)) // 2, 82, scale=2)

        # A horizontal bar showing strength relative to the threshold.
        bar_x, bar_y, bar_w, bar_h = 8, 104, d.width - 16, 10
        d.rect(bar_x, bar_y, bar_w, bar_h, 1)
        fraction = min(1.0, strength / (warn_threshold * 1.5))
        d.fill_rect(bar_x, bar_y, int(bar_w * fraction), bar_h, 1)

        # Status word at the very bottom.
        status = "HIGH FIELD" if over else "OK"
        draw_text(d, status, (d.width - text_width(status, 1)) // 2, 118, scale=1)
        d.show()

        # --- feedback outputs ---
        if over:
            hardware.led.set_color(255, 0, 0)
            now = time.ticks_ms()
            if time.ticks_diff(now, last_beep) > 800:
                hardware.buzzer.beep(60)
                last_beep = now
        else:
            hardware.led.set_color(0, 40, 0)

        time.sleep_ms(config.SENSOR_PERIOD_MS)


def calibrate_screen(hardware):
    # Walks the user through a hard-iron calibration: show instructions, wait
    # for a press, then sample while they rotate the device, drawing a progress
    # bar. Reports success or failure at the end.
    d = hardware.display

    # Instruction page.
    d.fill(0)
    draw_text(d, "CALIBRATE", 4, 4, scale=2)
    d.hline(0, 24, d.width, 1)
    draw_text(d, "Slowly rotate", 6, 36, scale=1)
    draw_text(d, "the device in", 6, 48, scale=1)
    draw_text(d, "all directions", 6, 60, scale=1)
    draw_text(d, "when you press", 6, 72, scale=1)
    draw_text(d, "the wheel.", 6, 84, scale=1)
    draw_text(d, "Press = start", 6, 104, scale=1)
    draw_text(d, "Left  = cancel", 6, 116, scale=1)
    d.show()

    # Wait for select (start) or left (cancel).
    while True:
        buttons = hardware.wheel.poll_buttons()
        if "select" in buttons:
            break
        if "left" in buttons:
            return
        time.sleep_ms(20)

    # Run calibration with a live progress bar.
    def on_progress(done, total):
        d.fill(0)
        draw_text(d, "CALIBRATING", 4, 4, scale=2)
        d.hline(0, 24, d.width, 1)
        draw_text(d, "Keep rotating", 6, 44, scale=1)
        bar_x, bar_y, bar_w, bar_h = 8, 70, d.width - 16, 14
        d.rect(bar_x, bar_y, bar_w, bar_h, 1)
        fraction = done / total
        d.fill_rect(bar_x, bar_y, int(bar_w * fraction), bar_h, 1)
        percent = "{:.0f}%".format(fraction * 100)
        draw_text(d, percent, (d.width - text_width(percent, 2)) // 2, 96, scale=2)
        d.show()
        # Spin the LED colour so it is clearly "working".
        hardware.led.set_color(0, 0, 60)

    hardware.led.set_color(0, 0, 60)
    ok = hardware.mag.calibrate(samples=200, on_progress=on_progress)
    hardware.led.off()

    # Result page.
    d.fill(0)
    if ok:
        draw_text(d, "DONE", 4, 20, scale=3)
        draw_text(d, "Offsets saved", 6, 70, scale=1)
        hardware.buzzer.double_beep()
    else:
        draw_text(d, "FAILED", 4, 20, scale=3)
        draw_text(d, "Not enough", 6, 66, scale=1)
        draw_text(d, "movement", 6, 78, scale=1)
        hardware.buzzer.beep(200)
    draw_text(d, "Press to go back", 4, 116, scale=1)
    d.show()

    while "select" not in hardware.wheel.poll_buttons() and \
          "left" not in hardware.wheel.poll_buttons():
        time.sleep_ms(20)


def about_screen(hardware):
    # A static information screen. Exit with left or select.
    d = hardware.display
    d.fill(0)
    draw_text(d, "HeartSense", 4, 6, scale=2)
    d.hline(0, 28, d.width, 1)
    draw_text(d, "Magnetic field", 6, 40, scale=1)
    draw_text(d, "strength meter", 6, 52, scale=1)
    draw_text(d, "MMC5603 sensor", 6, 72, scale=1)
    draw_text(d, "Pico powered", 6, 84, scale=1)
    draw_text(d, "Press to go back", 4, 116, scale=1)
    d.show()
    while True:
        buttons = hardware.wheel.poll_buttons()
        if "select" in buttons or "left" in buttons:
            return
        time.sleep_ms(20)
