"""Fan speed monitoring widget."""

from rich.text import Text

from .base_widget import BaseWidget

try:
    import psutil
except ImportError:
    psutil = None


class FanWidget(BaseWidget):
    """Displays the speed of system fans."""

    def __init__(self, **kwargs):
        super().__init__(title="Fans", **kwargs)
        self.refresh_data()

    def refresh_data(self) -> None:
        """Update the panel with current fan speeds."""
        text = Text()
        if psutil is None:
            text.append("psutil not available", style="dim")
        else:
            try:
                fans = psutil.sensors_fans()
                if not fans:
                    text.append("No fan sensors detected", style="dim")
                else:
                    has_data = False
                    for name, fan_list in fans.items():
                        for fan in fan_list:
                            has_data = True
                            label = fan.label or name
                            speed = fan.current
                            text.append(label, style="cyan")
                            text.append(": ", style="dim")
                            if speed is not None:
                                text.append(f"{speed} RPM", style="green")
                            else:
                                text.append("N/A", style="dim")
                            text.append("\n")
                    if not has_data:
                        text.append("No fan sensors detected", style="dim")
            except (AttributeError, PermissionError, OSError):
                text.append("Unable to read fan sensors", style="yellow")

        self.update_panel_content(text)
