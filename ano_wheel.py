# ano_wheel.py
# -----------------------------------------------------------------------------
# Driver for the Adafruit ANO rotary navigation encoder on its I2C "seesaw"
# breakout. The seesaw chip does the hard work of tracking the wheel and the
# five buttons, and we just read the results over I2C.
#
# The ANO gives us:
#   * a rotary wheel that spins endlessly and reports a running step count
#   * a centre push-button (used here as "select")
#   * four directional presses: up, down, left, right
#
# For the menu we mainly use the wheel to scroll and the centre button to
# select, with the directional presses available as extras (e.g. left = back).
# -----------------------------------------------------------------------------

import time

# seesaw "module base" addresses and function registers.
_STATUS_BASE = 0x00
_GPIO_BASE = 0x01
_ENCODER_BASE = 0x11

_STATUS_HW_ID = 0x01
_STATUS_SWRST = 0x7F

_GPIO_DIRCLR_BULK = 0x03   # set pins as inputs
_GPIO_BULK = 0x04          # read pin states
_GPIO_PULLENSET = 0x0B     # enable pull-up resistors

_ENCODER_POSITION = 0x30   # read the wheel's step count

# The five switches are wired to these seesaw GPIO pins on the ANO breakout.
_BUTTON_SELECT = 1   # centre press
_BUTTON_UP = 2
_BUTTON_LEFT = 3
_BUTTON_DOWN = 4
_BUTTON_RIGHT = 5

_ALL_BUTTONS = (
    _BUTTON_SELECT, _BUTTON_UP, _BUTTON_LEFT, _BUTTON_DOWN, _BUTTON_RIGHT
)


class AnoWheel:
    def __init__(self, i2c, address):
        self.i2c = i2c
        self.address = address
        # Last wheel position we saw, so we can report the change each time.
        self._last_position = 0
        # Remember which buttons were down last time, for edge detection.
        self._was_pressed = {pin: False for pin in _ALL_BUTTONS}
        self._setup()

    # --- low-level seesaw access ------------------------------------------

    def _write(self, base, reg, data=b""):
        self.i2c.writeto(self.address, bytes([base, reg]) + data)

    def _read(self, base, reg, length, delay_ms=5):
        # seesaw needs a short pause between asking for data and reading it.
        self.i2c.writeto(self.address, bytes([base, reg]))
        time.sleep_ms(delay_ms)
        return self.i2c.readfrom(self.address, length)

    def _setup(self):
        # Reset the seesaw chip, then configure the button pins as inputs with
        # pull-up resistors (so an unpressed button reads high, pressed reads low).
        self._write(_STATUS_BASE, _STATUS_SWRST, b"\xff")
        time.sleep_ms(20)

        mask = 0
        for pin in _ALL_BUTTONS:
            mask |= (1 << pin)
        mask_bytes = mask.to_bytes(4, "big")
        self._write(_GPIO_BASE, _GPIO_DIRCLR_BULK, mask_bytes)   # inputs
        self._write(_GPIO_BASE, _GPIO_PULLENSET, mask_bytes)     # pull-ups on

        # Record the starting wheel position as our reference.
        self._last_position = self._read_position()

    def is_connected(self):
        try:
            self._read(_STATUS_BASE, _STATUS_HW_ID, 1)
            return True
        except OSError:
            return False

    # --- wheel -------------------------------------------------------------

    def _read_position(self):
        data = self._read(_ENCODER_BASE, _ENCODER_POSITION, 4)
        value = int.from_bytes(data, "big")
        # The count is a signed 32-bit number.
        if value & 0x80000000:
            value -= 0x100000000
        return value

    def get_scroll(self):
        # Returns how many steps the wheel has turned since the last call.
        # Positive = one direction, negative = the other, 0 = no movement.
        position = self._read_position()
        delta = position - self._last_position
        self._last_position = position
        return delta

    # --- buttons -----------------------------------------------------------

    def _read_button_states(self):
        # Returns a dict of pin -> True if currently pressed.
        data = self._read(_GPIO_BASE, _GPIO_BULK, 4)
        bits = int.from_bytes(data, "big")
        pressed = {}
        for pin in _ALL_BUTTONS:
            # A pin reads low (0) when its button is pressed.
            pressed[pin] = (bits & (1 << pin)) == 0
        return pressed

    def poll_buttons(self):
        # Returns a set of button names that were *just pressed* (went from up
        # to down) since the last call. This gives one event per press rather
        # than repeating while held.
        names = {
            _BUTTON_SELECT: "select",
            _BUTTON_UP: "up",
            _BUTTON_DOWN: "down",
            _BUTTON_LEFT: "left",
            _BUTTON_RIGHT: "right",
        }
        just_pressed = set()
        states = self._read_button_states()
        for pin in _ALL_BUTTONS:
            now = states[pin]
            if now and not self._was_pressed[pin]:
                just_pressed.add(names[pin])
            self._was_pressed[pin] = now
        return just_pressed
