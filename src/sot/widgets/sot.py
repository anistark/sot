"""
SOT Widget
"""

from rich.align import Align
from rich.text import Text

from .base_widget import BaseWidget


class SotWidget(BaseWidget):
    """Simple Sot widget displaying the SOT symbol ≈"""
    
    def __init__(self, **kwargs):
        super().__init__(title="SOT", **kwargs)
        
    def on_mount(self):
        big_logo = Text()
        big_logo.append("\n\n")
        big_logo.append("    ≈", style="bold sky_blue3")
        big_logo.append("\n\n")
        
        centered_logo = Align.center(big_logo, vertical="middle")
        self.update_panel_content(centered_logo)
