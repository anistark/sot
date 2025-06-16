"""
Middle column widgets for the responsive 3-column layout.
"""

import psutil
from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widget import Widget


class HealthScoreWidget(Widget):
    """Health Score widget showing overall system health rating with breakdown."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def on_mount(self):
        self.panel = Panel(
            "",
            title="[b]Health Score[/]",
            title_align="left",
            border_style="bright_black",
            box=box.SQUARE,
        )
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
        scores['CPU'] = (cpu_score, 30)
        
        # Memory Health (25% weight)
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        if mem_percent < 60:
            mem_score = 100
        elif mem_percent < 85:
            mem_score = 80 - (mem_percent - 60) * 2
        else:
            mem_score = max(0, 30 - (mem_percent - 85) * 2)
        scores['Memory'] = (mem_score, 25)
        
        # Disk Health (20% weight)
        disk_usage = psutil.disk_usage('/')
        disk_percent = disk_usage.percent
        if disk_percent < 70:
            disk_score = 100
        elif disk_percent < 90:
            disk_score = 80 - (disk_percent - 70) * 2
        else:
            disk_score = max(0, 40 - (disk_percent - 90) * 4)
        scores['Disk'] = (disk_score, 20)
        
        # Process Health (15% weight)
        process_count = len(psutil.pids())
        if process_count < 200:
            proc_score = 100
        elif process_count < 400:
            proc_score = 80 - (process_count - 200) * 0.2
        else:
            proc_score = max(0, 40 - (process_count - 400) * 0.1)
        scores['Processes'] = (proc_score, 15)
        
        # Temperature Health (10% weight) - if available
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                avg_temp = sum(temp.current for sensor in temps.values() for temp in sensor) / sum(len(sensor) for sensor in temps.values())
                if avg_temp < 60:
                    temp_score = 100
                elif avg_temp < 80:
                    temp_score = 80 - (avg_temp - 60) * 2
                else:
                    temp_score = max(0, 40 - (avg_temp - 80) * 2)
                scores['Temperature'] = (temp_score, 10)
            else:
                scores['Temperature'] = (100, 10)  # Default if no sensors
        except:
            scores['Temperature'] = (100, 10)  # Default if not available
        
        # Calculate weighted average
        total_score = sum(score * weight for score, weight in scores.values())
        total_weight = sum(weight for _, weight in scores.values())
        overall_score = total_score / total_weight if total_weight > 0 else 100
        
        return overall_score, scores
        
    def get_score_color(self, score):
        """Get color based on score value"""
        if score >= 80:
            return "green"
        elif score >= 60:
            return "yellow"
        elif score >= 40:
            return "dark_orange"
        else:
            return "red3"

    def get_ascii_bar(self, score, width=8):
        """Generate ASCII bar graph for a score (0-100)"""
        filled_blocks = int((score / 100) * width)
        empty_blocks = width - filled_blocks
        
        if score >= 80:
            fill_char = "█"
            color = "green"
        elif score >= 60:
            fill_char = "▓"
            color = "yellow"
        elif score >= 40:
            fill_char = "▒"
            color = "dark_orange"
        else:
            fill_char = "░"
            color = "red3"
        
        bar = fill_char * filled_blocks + "·" * empty_blocks
        return f"[{color}]{bar}[/]"
        
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
        available_width = max(16, self.size.width - 4) if hasattr(self, 'size') else 18
        main_bar = self.get_ascii_bar(overall_score, available_width)
        score_color = self.get_score_color(overall_score)
        score_display = Text()
        score_display.append("▸ ", style="bright_cyan")
        score_display.append(f"{overall_score:.0f}", style=f"bold {score_color}")
        score_display.append("%", style="dim bright_white")

        status_lines = []
        component_width = max(16, self.size.width - 6) if hasattr(self, 'size') else 16
        
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
            spaces_needed = max(1, component_width - total_left_width - len(percentage_text))
            
            status_line.append(left_part, style="bright_white")
            status_line.append(" " * spaces_needed, style="")
            status_line.append(percentage_text, style=color)
            
            status_lines.append(status_line)

        content_lines = [
            Align.center(score_display),
            Align.center(main_bar),
            "",
            *status_lines
        ]
        
        from rich.console import Group
        content = Group(*content_lines)
        
        self.panel.renderable = content
        self.refresh()

    def render(self):
        return getattr(self, "panel", Panel("Loading...", title="[b]Health Score[/]"))


class LogoWidget(Widget):
    """Simple logo widget displaying the SOT symbol ≈"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def on_mount(self):
        big_logo = Text()
        big_logo.append("\n\n")
        big_logo.append("    ≈", style="bold sky_blue3")
        big_logo.append("\n\n")
        
        centered_logo = Align.center(big_logo, vertical="middle")
        
        self.panel = Panel(
            centered_logo,
            title="[b]SOT[/]",
            title_align="center",
            border_style="bright_black",
            box=box.SQUARE,
        )
        
    def render(self):
        return getattr(self, "panel", Panel("≈", title="[b]SOT[/]"))


class NetworkConnectionsWidget(Widget):
    """Network Connection Monitoring widget showing active connections."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation_frame = 0
        
    def on_mount(self):
        self.panel = Panel(
            "",
            title="[b]Network Connections[/]",
            title_align="left",
            border_style="bright_black",
            box=box.SQUARE,
        )
        self.update_content()
        self.set_interval(3.0, self.update_content)
        self.set_interval(0.5, self.animate_frame)
        
    def animate_frame(self):
        """Update animation frame counter"""
        self.animation_frame = (self.animation_frame + 1) % 8

    def get_animated_lock(self):
        """Get sick animated lock ASCII art for access denied"""
        frame = self.animation_frame
        glitch_chars = ["█", "▓", "▒", "░", "▄", "▀", "▌", "▐"]
        glitch = glitch_chars[frame % len(glitch_chars)]

        scan_patterns = [
            "╔═══════════════╗",
            "╔▓══════════════╗", 
            "╔═▓═════════════╗",
            "╔══▓════════════╗",
            "╔═══▓═══════════╗",
            "╔════▓══════════╗",
            "╔═════▓═════════╗",
            "╔══════▓════════╗"
        ]
        top_border = scan_patterns[frame % len(scan_patterns)]

        if frame % 4 < 2:
            lock_body = "▐█▌"
            lock_hook = "╭─╮"
        else:
            lock_body = "▐▓▌" 
            lock_hook = "╭▒╮"

        if frame % 6 < 3:
            warning = "░ACCESS░"
            warning2 = "░DENIED░"
        else:
            warning = "▓ACCESS▓"
            warning2 = "▓DENIED▓"

        static_line = glitch * 15
        
        lock_art = f"""{top_border}
║  {warning}  ║
║      {lock_hook}      ║
║      {lock_body}      ║
║   {warning2}   ║
║ {static_line[:13]} ║
║ UNAUTHORIZED ║
║   {glitch}{glitch} ZONE {glitch}{glitch}   ║
╚═══════════════╝"""
        
        return lock_art

    def update_content(self):
        """Update the network connections content with cyberpunk styling."""
        try:
            # Get network connections
            connections = psutil.net_connections(kind='inet')

            status_counts = {}
            local_ports = set()
            remote_hosts = set()
            
            for conn in connections:
                status = conn.status if conn.status else "UNKNOWN"
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if conn.laddr:
                    local_ports.add(conn.laddr.port)
                if conn.raddr:
                    remote_hosts.add(conn.raddr.ip)

            matrix_lines = []

            established = status_counts.get('ESTABLISHED', 0)
            listening = status_counts.get('LISTEN', 0)
            time_wait = status_counts.get('TIME_WAIT', 0)

            status_line1 = Text()
            status_line1.append("▲ ACTIVE: ", style="bright_green")
            status_line1.append(f"{established:>3}", style="bold bright_white")
            
            status_line2 = Text()
            status_line2.append("◆ LISTEN: ", style="bright_cyan")
            status_line2.append(f"{listening:>3}", style="bold bright_white")
            
            status_line3 = Text()
            status_line3.append("○ WAIT  : ", style="bright_yellow")
            status_line3.append(f"{time_wait:>3}", style="bold bright_white")
            matrix_lines.extend([status_line1, status_line2, status_line3])
            matrix_lines.append(Text(""))
            
            flow_line = Text()
            flow_line.append(f"PORTS:{len(local_ports):>2} ", style="bright_cyan")
            flow_line.append("◄─►", style="bright_white")
            flow_line.append(f" HOSTS:{len(remote_hosts):>2}", style="bright_green")
            matrix_lines.append(flow_line)
            matrix_lines.append(Text(""))
            matrix_lines.append(Text("DATA STREAMS:", style="dim bright_white"))
            
            conn_count = 0
            for conn in connections[:3]:
                if conn.raddr and conn.status == 'ESTABLISHED':
                    stream_line = Text()
                    stream_line.append("▸ ", style="bright_cyan")
                    stream_line.append(f"{conn.raddr.ip}", style="bright_green")
                    stream_line.append(f":{conn.raddr.port}", style="bright_yellow")
                    matrix_lines.append(stream_line)
                    conn_count += 1
                if conn_count >= 3:
                    break
            
            if conn_count == 0:
                matrix_lines.append(Text("▸ NO ACTIVE STREAMS", style="dim bright_black"))
            
            from rich.console import Group
            content = Group(*matrix_lines)
            
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            lock_art = self.get_animated_lock()
            content = Text(lock_art, style="bright_red", justify="center")
            
        except Exception as e:
            content = Text(f"ERROR: {str(e)[:15]}...", style="bright_red", justify="center")
        
        self.panel.renderable = content
        self.refresh()

    def render(self):
        return getattr(self, "panel", Panel("Loading...", title="[b]Network Connections[/]"))
