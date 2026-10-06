from math import ceil

num_to_blockchar = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

# Common fonts only have coarse top-anchored blocks, so eighths are rounded.
num_to_blockchar_upside_down = [" ", "▔", "▔", "▀", "▀", "▀", "▀", "█", "█"]


class BlockCharStream:
    """Bar-chart stream with one sample per cell; same interface as BrailleStream."""

    def __init__(
        self,
        width: int,
        height: int,
        minval: float,
        maxval: float,
        flipud: bool = False,
    ):
        self.width = width
        self.height = height
        self.minval = minval
        self.maxval = maxval
        self.flipud = flipud
        self.lookup = num_to_blockchar_upside_down if flipud else num_to_blockchar
        self.graph = [" " * width] * height
        self.values: list[float] = [minval] * width
        self.last_value: float = minval

    def _column(self, value: float) -> list[str]:
        diff = (self.maxval - self.minval) or 1
        k = ceil((value - self.minval) / diff * 8 * self.height)
        k = max(0, min(k, 8 * self.height))

        blocks = [8] * (k // 8)
        if k % 8 > 0:
            blocks += [k % 8]
        blocks += [0] * (self.height - len(blocks))

        chars = [self.lookup[i] for i in blocks]
        return chars if self.flipud else chars[::-1]

    def add_value(self, value: float):
        for k, char in enumerate(self._column(value)):
            self.graph[k] = self.graph[k][1:] + char

        self.values = self.values[1:] + [value]
        self.last_value = value

    def _rebuild(self):
        columns = [self._column(value) for value in self.values]
        self.graph = ["".join(row) for row in zip(*columns)]

    def reset_width(self, width: int):
        width = max(1, width)
        if width == self.width:
            return
        if width > self.width:
            self.values = [self.minval] * (width - self.width) + self.values
        else:
            self.values = self.values[-width:]
        self.width = width
        self._rebuild()

    def reset_height(self, height: int):
        height = max(1, height)
        if height == self.height:
            return
        self.height = height
        self._rebuild()
