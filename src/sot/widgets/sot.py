"""
SOT Widget
"""

import math
import random

from rich.align import Align
from rich.text import Text

from .._theme import theme
from ..tui import refresh
from .base_widget import BaseWidget


class SotLogoWidget(BaseWidget):
    # TODO: Figure out something cool to do with this widget.

    def __init__(self, **kwargs):
        super().__init__(title="SOT", **kwargs)
        self.animation_frame = 0
        self.wave_chars = ["⠀", "⠁", "⠃", "⠇", "⡇", "⡗", "⡷", "⡿", "⣿"]

    def on_mount(self):
        self.update_sine_wave()
        self.every(refresh.ANIMATION, self.animate_wave)

    def animate_wave(self):
        """Update animation frame and regenerate sine wave."""
        self.animation_frame += 1
        self.update_sine_wave()

    def get_sine_wave_line(self, width, y_offset, phase_shift=0.0):
        """Generate a single line of sine wave using Braille characters."""
        if width < 10:
            return "~" * width

        line = []
        for x in range(width):
            angle = (x / width * 4 * math.pi) + phase_shift
            sine_value = math.sin(angle)

            adjusted_value = sine_value + y_offset

            intensity = max(0, min(8, int((adjusted_value + 1) * 4)))

            if intensity < len(self.wave_chars):
                line.append(self.wave_chars[intensity])
            else:
                line.append("⣿")

        return "".join(line)

    def update_sine_wave(self):
        """Generate and display animated sine wave."""
        t = theme()
        c = t.colors
        logo = t.design.logo
        tagline = t.design.tagline

        # Leave room for the borders, the gap, the logo and the tagline.
        reserved = 3 + len(logo) + (1 if tagline else 0)
        width = max(20, getattr(self.size, "width", 40) - 4)
        height = max(1, min(7, getattr(self.size, "height", 10) - reserved))
        phase = self.animation_frame * 0.2

        lines = []

        for i in range(height):
            line_phase = phase + (i * 0.3)
            y_offset = (i - height / 2) * 0.3

            wave_line = self.get_sine_wave_line(width, y_offset, line_phase)

            if i < height // 3:
                style = c.wave[0]
            elif i < 2 * height // 3:
                style = c.wave[1]
            else:
                style = c.wave[2]

            lines.append(Text(wave_line, style=style))

        logo_width = max(len(line) for line in (*logo, tagline or ""))

        big_sot_text = Text("\n\n")
        glitching = t.design.glitch and self.animation_frame % 40 in (0, 1, 4)
        for line in logo:
            line = line.center(logo_width)
            style = f"bold {c.logo}"
            if glitching:
                shift = random.choice((-2, -1, 1, 2))
                line = line[shift:] + line[:shift]
                style = f"bold {random.choice((c.danger, c.secondary, c.logo))}"
            big_sot_text.append(line, style=style)
            big_sot_text.append("\n")
        if tagline:
            big_sot_text.append(tagline.center(logo_width), style=c.muted)
            big_sot_text.append("\n")
        big_sot_text.right_crop(1)

        wave_display = Text()
        for i, line in enumerate(lines):
            if i > 0:
                wave_display.append("\n")
            wave_display.append_text(line)

        combined_display = Text()
        combined_display.append_text(wave_display)
        combined_display.append_text(big_sot_text)

        centered_wave = Align.center(combined_display, vertical="middle")
        self.update_panel_content(centered_wave)

    async def on_resize(self, event):
        """Handle widget resize by regenerating the wave."""
        self.update_sine_wave()
