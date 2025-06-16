"""
SOT Widgets Module

This module contains all the UI widgets for the SOT (System Observation Tool).
Each widget is responsible for displaying specific system information.
"""

from .base_widget import BaseWidget
from .cpu import CPUWidget
from .disk import DiskWidget
from .health_score import HealthScoreWidget
from .info import InfoWidget
from .memory import MemoryWidget
from .network import NetworkWidget
from .network_connections import NetworkConnectionsWidget
from .processes import ProcessesWidget
from .sot import SotWidget

__all__ = [
    "BaseWidget",
    "CPUWidget",
    "DiskWidget",
    "HealthScoreWidget",
    "InfoWidget",
    "SotWidget",
    "MemoryWidget",
    "NetworkWidget",
    "NetworkConnectionsWidget",
    "ProcessesWidget",
]
