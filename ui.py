# ui.py
# -----------------------------------------------------------------------------
# The smooth, scrollable user-interface framework.
#
# The two ideas that make the UI feel smooth:
#
#  1. Every frame is drawn from scratch into the OLED's buffer and flipped to
#     the screen. Nothing is drawn "in place", so we can show the menu at any
#     scroll position, including part-way between two items.
#
#  2. The menu has a *target* scroll position (the item the wheel has landed on)
#     and a *current* scroll position that eases toward the target a little each
#     frame. That gliding motion is what makes scrolling look animated rather
#     than jumping instantly from one item to the next. The same easing is used
#     for the moving selection highlight.
# -----------------------------------------------------------------------------

import math


def draw_text(display, text, x, y, scale=1, color=1):
    # Draws text using the FrameBuffer's built-in 8x8 font, optionally scaled up
    # so it is readable on the 128x128 screen.
    #
    # scale=1 draws the normal 8-pixel font. scale=2 doubles every pixel, and
    # so on. We draw each character into a tiny temporary buffer, then copy it
    # out pixel-by-pixel at the requested size.
    if scale == 1:
        display.text(text, x, y, color)
        return

    import framebuf
    char_w = 8
    for index, char in enumerate(text):
        # Render one character into an 8x8 buffer.
        tmp = bytearray(char_w)
        fb = framebuf.FrameBuffer(tmp, char_w, char_w, framebuf.MONO_VLSB)
        fb.text(char, 0, 0, 1)
        # Copy it out, scaled.
        base_x = x + index * char_w * scale
        for px in range(char_w):
            for py in range(char_w):
                if fb.pixel(px, py):
                    display.fill_rect(
                        base_x + px * scale,
                        y + py * scale,
                        scale, scale, color,
                    )


def text_width(text, scale=1):
    return len(text) * 8 * scale


class ScrollMenu:
    # A vertical list of options that scrolls smoothly as the wheel turns.
    #
    # items: a list of strings to show.
    # The caller turns the wheel (scroll_by), presses select, and each frame
    # calls draw() to render the current animated state.

    def __init__(self, display, items, title=""):
        self.display = display
        self.items = items
        self.title = title

        # Which item is selected (an integer index).
        self.selected = 0

        # row_height is how many pixels tall each menu row is.
        self.row_height = 22
        # The selection highlight glides; this is its animated y position.
        self._highlight_y = self._row_top(0)
        # The list itself glides vertically so the selected item stays centred.
        self._scroll_y = 0.0
        self._target_scroll_y = 0.0

        # How quickly the animations catch up to their target (0..1). Higher is
        # snappier, lower is floatier. 0.35 feels smooth without lagging.
        self.ease = 0.35

    # --- geometry helpers --------------------------------------------------

    def _row_top(self, index):
        # The y position of a row, before scrolling is applied.
        top_margin = 34 if self.title else 6
        return top_margin + index * self.row_height

    def _update_targets(self):
        # Keep the selected row roughly centred on screen by scrolling the list.
        screen_middle = self.display.height // 2
        selected_centre = self._row_top(self.selected) + self.row_height // 2
        self._target_scroll_y = selected_centre - screen_middle
        # Don't scroll past the top of the list.
        if self._target_scroll_y < 0:
            self._target_scroll_y = 0

    # --- input -------------------------------------------------------------

    def scroll_by(self, steps):
        # Move the selection by a number of wheel steps (can be + or -).
        if steps == 0:
            return
        self.selected += steps
        # Clamp to the ends of the list (no wrap-around).
        if self.selected < 0:
            self.selected = 0
        if self.selected > len(self.items) - 1:
            self.selected = len(self.items) - 1
        self._update_targets()

    def current_item(self):
        return self.items[self.selected]

    # --- animation + drawing ----------------------------------------------

    def _animate(self):
        # Ease the current scroll position toward its target.
        self._scroll_y += (self._target_scroll_y - self._scroll_y) * self.ease
        # Ease the highlight toward the selected row.
        target_highlight = self._row_top(self.selected)
        self._highlight_y += (target_highlight - self._highlight_y) * self.ease

    def _is_settled(self):
        # True when the animation has essentially finished, so the main loop
        # can stop redrawing and save power if it wants to.
        return (
            abs(self._target_scroll_y - self._scroll_y) < 0.5
            and abs(self._row_top(self.selected) - self._highlight_y) < 0.5
        )

    def draw(self):
        self._animate()
        d = self.display
        d.fill(0)

        # Title bar.
        if self.title:
            draw_text(d, self.title, 4, 6, scale=2)
            d.hline(0, 28, d.width, 1)

        scroll = int(self._scroll_y)
        highlight_screen_y = int(self._highlight_y - scroll)

        # Draw the moving selection highlight as a filled rounded-ish bar.
        d.fill_rect(2, highlight_screen_y - 2, d.width - 4, self.row_height, 1)

        # Draw each visible menu item.
        for index, label in enumerate(self.items):
            row_y = self._row_top(index) - scroll
            # Skip rows that are off-screen (keeps it fast with long lists).
            if row_y < -self.row_height or row_y > d.height:
                continue
            # The selected row sits on the white highlight, so draw it in black;
            # the others are white text on black.
            if index == self.selected:
                color = 0
            else:
                color = 1
            draw_text(d, label, 10, row_y + 3, scale=2, color=color)

        # A little scrollbar on the right if the list is longer than the screen.
        self._draw_scrollbar()

        d.show()

    def _draw_scrollbar(self):
        d = self.display
        total = len(self.items)
        if total <= 1:
            return
        full_height = total * self.row_height
        if full_height <= d.height:
            return
        bar_x = d.width - 3
        # Proportional thumb.
        visible_fraction = d.height / full_height
        thumb_height = max(8, int(d.height * visible_fraction))
        max_scroll = full_height - d.height
        if max_scroll <= 0:
            return
        progress = min(1.0, max(0.0, self._scroll_y / max_scroll))
        thumb_y = int(progress * (d.height - thumb_height))
        d.fill_rect(bar_x, thumb_y, 2, thumb_height, 1)
