"""
SOT Widget
"""

import math

from rich.align import Align
from rich.text import Text

from .base_widget import BaseWidget


class SotWidget(BaseWidget):
    # TODO: Figure out something cool to do with this widget.

    def __init__(self, **kwargs):
        super().__init__(title="SOT", **kwargs)
        self.animation_frame = 0
        self.wave_chars = ["⠀", "⠁", "⠃", "⠇", "⡇", "⡗", "⡷", "⡿", "⣿"]

    def on_mount(self):
        self.update_sine_wave()
        self.set_interval(0.1, self.animate_wave)

    def animate_wave(self):
        """Update animation frame and regenerate sine wave."""
        self.animation_frame += 1
        self.update_sine_wave()

    def get_sine_wave_line(self, width, y_offset, phase_shift=0):
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
        width = getattr(self.size, "width", 40) - 4
        height = getattr(self.size, "height", 10) - 3

        width = max(20, width)
        height = max(4, min(7, height))

        phase = self.animation_frame * 0.2

        lines = []

        for i in range(height):
            line_phase = phase + (i * 0.3)
            y_offset = (i - height / 2) * 0.3

            wave_line = self.get_sine_wave_line(width, y_offset, line_phase)

            if i < height // 3:
                style = "bright_cyan"
            elif i < 2 * height // 3:
                style = "sky_blue3"
            else:
                style = "aquamarine3"

            lines.append(Text(wave_line, style=style))

        big_sot_text = Text()
        big_sot_text.append("\n")
        big_sot_text.append("\n")
        big_sot_text.append("      ▄▀▀  ▄▀▀▄  ▀█▀      ", style="bold bright_yellow")
        big_sot_text.append("\n")
        big_sot_text.append("      ▀▀▄  █  █   █       ", style="bold bright_yellow")
        big_sot_text.append("\n")
        big_sot_text.append("      ▄▄▀  ▀▄▄▀   █       ", style="bold bright_yellow")
        big_sot_text.append("\n")

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
