# magnetometer.py
# -----------------------------------------------------------------------------
# Driver for the MMC5603 3-axis magnetometer, talking over I2C.
#
# The chip measures the magnetic field along three axes (x, y, z). We mostly
# care about the total field strength, which is the length of that 3D vector.
#
# Two features of the MMC5603 make the readings cleaner, and we use both:
#   * SET / RESET: the chip can flip the polarity of its internal sensing
#     element. Taking one reading after a SET and one after a RESET, then
#     combining them, cancels out the sensor's own built-in offset.
#   * Hard-iron calibration: nearby metal (screws, the switch spring, caps) adds
#     a constant offset to each axis. We measure that offset once and subtract
#     it from every future reading.
# -----------------------------------------------------------------------------

import time
import math
import struct

# MMC5603 register addresses (from the datasheet).
_REG_XOUT0 = 0x00      # first of the six data registers
_REG_STATUS = 0x18     # status flags, including "measurement done"
_REG_ODR = 0x1A        # output data rate
_REG_CTRL0 = 0x1B      # control register 0 (triggers, SET/RESET)
_REG_CTRL1 = 0x1C      # control register 1 (bandwidth, soft reset)
_REG_CTRL2 = 0x1D      # control register 2 (continuous mode)
_REG_PRODUCT_ID = 0x39 # should read back a known value

_PRODUCT_ID_VALUE = 0x10

# Bit masks for CTRL0.
_CTRL0_TAKE_MEAS_M = 0x01   # start a magnetic measurement
_CTRL0_DO_SET = 0x08        # perform a SET
_CTRL0_DO_RESET = 0x10      # perform a RESET

# Bit mask for the "measurement done" flag in the status register.
_STATUS_MEAS_DONE = 0x40

# The MMC5603 reports 20-bit values. One microtesla is this many counts.
# (16384 counts per gauss, and 1 gauss = 100 microtesla.)
_COUNTS_PER_UT = 163.84

# The zero-field reading sits in the middle of the 20-bit range.
_ZERO_OFFSET_COUNTS = 524288   # = 2 ** 19


class Magnetometer:
    def __init__(self, i2c, address):
        self.i2c = i2c
        self.address = address
        # Hard-iron offsets (in microtesla) for each axis, found by calibration.
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_z = 0.0
        self._reset_chip()

    # --- low-level helpers -------------------------------------------------

    def _write_register(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes([value]))

    def _read_registers(self, register, length):
        return self.i2c.readfrom_mem(self.address, register, length)

    def _reset_chip(self):
        # Software reset, then wait for the chip to come back.
        self._write_register(_REG_CTRL1, 0x80)
        time.sleep_ms(20)

    def is_connected(self):
        # Reads the product-ID register and checks it matches the expected value.
        try:
            value = self._read_registers(_REG_PRODUCT_ID, 1)[0]
            return value == _PRODUCT_ID_VALUE
        except OSError:
            return False

    # --- taking a raw measurement -----------------------------------------

    def _trigger_and_wait(self, extra_bits=0):
        # Start a single measurement (optionally also doing a SET or RESET),
        # then wait until the chip says it is finished.
        self._write_register(_REG_CTRL0, _CTRL0_TAKE_MEAS_M | extra_bits)
        # Wait for the done flag, but never loop forever.
        deadline = time.ticks_add(time.ticks_ms(), 50)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            status = self._read_registers(_REG_STATUS, 1)[0]
            if status & _STATUS_MEAS_DONE:
                break
            time.sleep_ms(1)

    def _read_raw_axes(self):
        # Reads the six data registers and converts them to microtesla,
        # before any offset is removed.
        data = self._read_registers(_REG_XOUT0, 9)
        # Each axis is 20 bits spread over three bytes: high, mid, low-nibble.
        def axis(hi, mid, lo_nibble):
            raw = (data[hi] << 12) | (data[mid] << 4) | (data[lo_nibble] >> 4)
            return (raw - _ZERO_OFFSET_COUNTS) / _COUNTS_PER_UT

        x = axis(0, 1, 6)
        y = axis(2, 3, 7)
        z = axis(4, 5, 8)
        return (x, y, z)

    # --- public reading methods -------------------------------------------

    def read_axes(self):
        # Returns the calibrated (x, y, z) field in microtesla.
        #
        # We take one reading after a SET and one after a RESET. The sensor's
        # own offset flips sign between the two, so averaging the right way
        # removes it. The real field is half the difference of the two.
        self._trigger_and_wait(_CTRL0_DO_SET)
        set_x, set_y, set_z = self._read_raw_axes()

        self._trigger_and_wait(_CTRL0_DO_RESET)
        reset_x, reset_y, reset_z = self._read_raw_axes()

        x = (set_x - reset_x) / 2.0
        y = (set_y - reset_y) / 2.0
        z = (set_z - reset_z) / 2.0

        # Subtract the hard-iron offsets found during calibration.
        x -= self.offset_x
        y -= self.offset_y
        z -= self.offset_z
        return (x, y, z)

    def read_strength(self):
        # Returns the total field strength in microtesla (the length of the
        # x, y, z vector). This is the main number the device displays.
        x, y, z = self.read_axes()
        return math.sqrt(x * x + y * y + z * z)

    # --- calibration -------------------------------------------------------

    def calibrate(self, samples=200, on_progress=None):
        # Hard-iron calibration.
        #
        # The user should slowly rotate the device through all orientations
        # while this runs. We record the smallest and largest value seen on
        # each axis; the offset is the midpoint of that range.
        #
        # on_progress, if given, is called as on_progress(done, total) so the
        # UI can draw a progress bar.
        min_x = min_y = min_z = 1e9
        max_x = max_y = max_z = -1e9

        # Temporarily clear existing offsets so we measure raw field.
        saved = (self.offset_x, self.offset_y, self.offset_z)
        self.offset_x = self.offset_y = self.offset_z = 0.0

        for i in range(samples):
            x, y, z = self.read_axes()
            min_x = min(min_x, x); max_x = max(max_x, x)
            min_y = min(min_y, y); max_y = max(max_y, y)
            min_z = min(min_z, z); max_z = max(max_z, z)
            if on_progress:
                on_progress(i + 1, samples)
            time.sleep_ms(20)

        # If the user barely moved the device the range is tiny and the result
        # is meaningless, so keep the old offsets in that case.
        spread = (max_x - min_x) + (max_y - min_y) + (max_z - min_z)
        if spread < 1.0:
            self.offset_x, self.offset_y, self.offset_z = saved
            return False

        self.offset_x = (max_x + min_x) / 2.0
        self.offset_y = (max_y + min_y) / 2.0
        self.offset_z = (max_z + min_z) / 2.0
        return True
