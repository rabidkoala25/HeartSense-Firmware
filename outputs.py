# outputs.py
# -----------------------------------------------------------------------------
# Simple helpers for the two output devices that are not the screen:
#   * the passive piezo buzzer (beeps for feedback / alerts)
#   * the single NeoPixel RGB status LED
# -----------------------------------------------------------------------------

import time
import machine
import neopixel

import config


class Buzzer:
    # Drives the passive piezo. A passive piezo makes no sound on a steady
    # voltage, so we feed it a PWM square wave at its resonant frequency.
    def __init__(self, pin_number):
        self.pwm = machine.PWM(machine.Pin(pin_number))
        self.pwm.freq(config.BUZZER_FREQUENCY)
        self.pwm.duty_u16(0)   # start silent (0% duty = no sound)

    def _on(self):
        self.pwm.duty_u16(32768)   # 50% duty square wave

    def _off(self):
        self.pwm.duty_u16(0)

    def beep(self, duration_ms=40):
        # One short blocking beep.
        self._on()
        time.sleep_ms(duration_ms)
        self._off()

    def double_beep(self):
        self.beep(40)
        time.sleep_ms(40)
        self.beep(40)


class StatusLed:
    # Wraps the single NeoPixel. Colours are given as (red, green, blue),
    # each 0-255.
    def __init__(self, pin_number, count):
        self.np = neopixel.NeoPixel(machine.Pin(pin_number), count)
        self.count = count
        self._current = (0, 0, 0)
        self.off()

    def set_color(self, red, green, blue):
        self._current = (red, green, blue)
        # This LED wants plain R, G, B order.
        for i in range(self.count):
            self.np[i] = (red, green, blue)
        self.np.write()

    def off(self):
        self.set_color(0, 0, 0)

    # These two let the magnetometer blank the LED during a reading and then
    # restore whatever colour it was showing.
    def save_and_blank(self):
        self._saved = self._current
        # Write black directly without changing _current, so restore works.
        for i in range(self.count):
            self.np[i] = (0, 0, 0)
        self.np.write()

    def restore(self):
        red, green, blue = getattr(self, "_saved", (0, 0, 0))
        self.set_color(red, green, blue)
