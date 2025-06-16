"""
SOT Widget
"""

from rich.align import Align
from rich.text import Text

from .base_widget import BaseWidget


class SotWidget(BaseWidget):
    """SOT widget displaying ASCII art logo."""
    
    def __init__(self, **kwargs):
        super().__init__(title="SOT", **kwargs)
        
    def on_mount(self):
        ascii_art = """≈"""

        ascii_text = Text(ascii_art, style="bold sky_blue3")
        centered_ascii = Align.center(ascii_text, vertical="middle")
        self.update_panel_content(centered_ascii)
