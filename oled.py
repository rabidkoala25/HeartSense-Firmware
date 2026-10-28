# oled.py
# -----------------------------------------------------------------------------
# Driver for the Pimoroni 1.12" 128x128 monochrome OLED over I2C.
#
# This OLED uses an SH1107 controller. We keep a full-screen buffer in memory
# using MicroPython's built-in FrameBuffer (which gives us text, lines, rects
# and pixels for free), then push the whole buffer to the display in one go
# when we call show().
#
# Keeping everything in a buffer and redrawing each frame is what lets the UI
# animate smoothly: we can draw a menu at any sub-pixel scroll position and
# flip it to the screen many times a second.
# -----------------------------------------------------------------------------

import time
import framebuf

# SH1107 command bytes.
_SET_DISP = 0xAE            # 0xAE off, 0xAF on
_SET_MEM_ADDR_MODE = 0x20
_SET_CONTRAST = 0x81
_SET_SEG_REMAP = 0xA0
_SET_NORM_INV = 0xA6
_SET_MUX_RATIO = 0xA8
_SET_COM_OUT_DIR = 0xC0
_SET_DISP_OFFSET = 0xD3
_SET_DISP_CLK_DIV = 0xD5
_SET_PRECHARGE = 0xD9
_SET_VCOM_DESEL = 0xDB
_SET_DISP_START_LINE = 0xDC
_SET_CHARGE_PUMP = 0xAD


class OLED(framebuf.FrameBuffer):
    def __init__(self, i2c, address, width, height):
        self.i2c = i2c
        self.address = address
        self.width = width
        self.height = height
        # One bit per pixel; the SH1107 is organised in vertical byte columns.
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self._init_display()

    def _command(self, *commands):
        for c in commands:
            # Control byte 0x80 means "a command byte follows".
            self.i2c.writeto(self.address, bytes([0x80, c]))

    def _init_display(self):
        for cmd in (
            _SET_DISP | 0x00,            # display off
            _SET_DISP_CLK_DIV, 0x51,
            _SET_MUX_RATIO, 0x7F,        # 128 rows
            _SET_DISP_OFFSET, 0x00,
            _SET_DISP_START_LINE, 0x00,
            _SET_CHARGE_PUMP, 0x8A,      # enable internal charge pump
            _SET_MEM_ADDR_MODE, 0x00,
            _SET_SEG_REMAP | 0x01,
            _SET_COM_OUT_DIR | 0x08,
            _SET_CONTRAST, 0x80,
            _SET_PRECHARGE, 0x22,
            _SET_VCOM_DESEL, 0x35,
            _SET_NORM_INV,               # normal (not inverted)
            _SET_DISP | 0x01,            # display on
        ):
            self._command(cmd)
        time.sleep_ms(100)
        self.fill(0)
        self.show()

    def show(self):
        # Push the whole buffer to the display, one page (8-pixel row band)
        # at a time.
        for page in range(self.pages):
            self._command(
                0xB0 | page,             # set page address
                0x00,                    # lower column = 0
                0x10,                    # higher column = 0
            )
            start = self.width * page
            # 0x40 control byte means "pixel data follows".
            self.i2c.writeto(
                self.address,
                bytes([0x40]) + self.buffer[start:start + self.width],
            )

    def contrast(self, value):
        self._command(_SET_CONTRAST, value & 0xFF)
