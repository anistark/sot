"""
Health Score Widget

Displays overall system health with component breakdown and cyberpunk styling.
"""

import psutil
from rich.align import Align
from rich.console import Group
from rich.text import Text

from .base_widget import BaseWidget


class HealthScoreWidget(BaseWidget):
    """Health Score widget showing overall system health rating with breakdown."""

    def __init__(self, **kwargs):
        super().__init__(title="Health Score", **kwargs)

    def on_mount(self):
        self.update_content()
        self.set_interval(5.0, self.update_content)

    def calculate_health_score(self):
        """Calculate overall system health score (0-100)"""
        scores = {}

        # CPU Health (30% weight)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent < 50:
            cpu_score = 100
        elif cpu_percent < 80:
            cpu_score = 80 - (cpu_percent - 50) * 2
        else:
            cpu_score = max(0, 20 - (cpu_percent - 80) * 2)
        scores["CPU"] = (cpu_score, 30)

        # Memory Health (25% weight)
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        if mem_percent < 60:
            mem_score = 100
        elif mem_percent < 85:
            mem_score = 80 - (mem_percent - 60) * 2
        else:
            mem_score = max(0, 30 - (mem_percent - 85) * 2)
        scores["Memory"] = (mem_score, 25)

        # Disk Health (20% weight)
        disk_usage = psutil.disk_usage("/")
        disk_percent = disk_usage.percent
        if disk_percent < 70:
            disk_score = 100
        elif disk_percent < 90:
            disk_score = 80 - (disk_percent - 70) * 2
        else:
            disk_score = max(0, 40 - (disk_percent - 90) * 4)
        scores["Disk"] = (disk_score, 20)

        # Process Health (15% weight)
        process_count = len(psutil.pids())
        if process_count < 200:
            proc_score = 100
        elif process_count < 400:
            proc_score = 80 - (process_count - 200) * 0.2
        else:
            proc_score = max(0, 40 - (process_count - 400) * 0.1)
        scores["Processes"] = (proc_score, 15)

        # Temperature Health (10% weight) - if available
        try:
            temps = getattr(psutil, "sensors_temperatures", lambda: {})() or {}
            if temps:
                avg_temp = sum(
                    temp.current for sensor in temps.values() for temp in sensor
                ) / sum(len(sensor) for sensor in temps.values())
                if avg_temp < 60:
                    temp_score = 100
                elif avg_temp < 80:
                    temp_score = 80 - (avg_temp - 60) * 2
                else:
                    temp_score = max(0, 40 - (avg_temp - 80) * 2)
                scores["Temperature"] = (temp_score, 10)
            else:
                scores["Temperature"] = (100, 10)  # Default if no sensors
        except Exception:
            scores["Temperature"] = (100, 10)  # Default if not available

        # Calculate weighted average
        total_score = sum(score * weight for score, weight in scores.values())
        total_weight = sum(weight for _, weight in scores.values())
        overall_score = total_score / total_weight if total_weight > 0 else 100

        return overall_score, scores

    def get_score_color(self, score):
        """Get color based on score value"""
        if score >= 80:
            return "bright_green"
        elif score >= 60:
            return "bright_cyan"
        elif score >= 40:
            return "bright_yellow"
        else:
            return "bright_red"

    def get_ascii_bar(self, score, width=8):
        """Generate ASCII bar graph for a score (0-100)"""
        filled_blocks = int((score / 100) * width)
        empty_blocks = width - filled_blocks

        if score >= 80:
            fill_char = "█"
            color = "bright_green"
        elif score >= 60:
            fill_char = "▓"
            color = "bright_cyan"
        elif score >= 40:
            fill_char = "▒"
            color = "bright_yellow"
        else:
            fill_char = "░"
            color = "bright_red"

        bar = fill_char * filled_blocks + "░" * empty_blocks
        return f"[{color}]{bar}[/]"

    def update_content(self):
        """Update the health score content with cyberpunk styling."""
        overall_score, component_scores = self.calculate_health_score()
        available_width = max(16, self.size.width - 4) if hasattr(self, "size") else 18
        main_bar = self.get_ascii_bar(overall_score, available_width)
        score_color = self.get_score_color(overall_score)
        score_display = Text()
        score_display.append("▸ ", style="bright_cyan")
        score_display.append(f"{overall_score:.0f}", style=f"bold {score_color}")
        score_display.append("%", style="dim bright_white")

        status_lines = []
        component_width = max(16, self.size.width - 6) if hasattr(self, "size") else 16

        for component, (score, weight) in component_scores.items():
            color = self.get_score_color(score)

            if score >= 80:
                indicator = "●"
                ind_color = "bright_green"
            elif score >= 60:
                indicator = "◐"
                ind_color = "bright_cyan"
            elif score >= 40:
                indicator = "◑"
                ind_color = "bright_yellow"
            else:
                indicator = "○"
                ind_color = "bright_red"

            status_line = Text()
            status_line.append(f"{indicator} ", style=ind_color)
            component_name = component if component != "Processes" else "Procs"
            if component == "Temperature":
                component_name = "Temperature"

            percentage_text = f"{score:>3.0f}%"
            left_part = f"{component_name}"

            total_left_width = 2 + len(left_part)
            spaces_needed = max(
                1, component_width - total_left_width - len(percentage_text)
            )

            status_line.append(left_part, style="bright_white")
            status_line.append(" " * spaces_needed, style="")
            status_line.append(percentage_text, style=color)

            status_lines.append(status_line)

        content_lines = [
            Align.center(score_display),
            Align.center(main_bar),
            "",
            *status_lines,
        ]

        content = Group(*content_lines)
        self.update_panel_content(content)
