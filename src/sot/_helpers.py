# https://stackoverflow.com/a/1094933/353337
def sizeof_fmt(num, fmt=".0f", suffix: str = "iB", sep=" "):
    assert num >= 0
    for unit in ["B", "K", "M", "G", "T", "P", "E", "Z"]:
        # actually 1024, but be economical with the return string size:
        if unit != "B":
            unit += suffix

        if num < 1000:
            string = f"{{:{fmt}}}".format(num)
            return f"{string}{sep}{unit}"
        num /= 1024
    string = f"{{:{fmt}}}".format(num)
    return f"{string}{sep}Y{suffix}"


def throughput_fmt(mbps, fmt=".1f"):
    """Format throughput in MB/s with appropriate unit scaling."""
    assert mbps >= 0
    for unit in ["MB/s", "GB/s", "TB/s"]:
        if mbps < 1000:
            string = f"{{:{fmt}}}".format(mbps)
            return f"{string} {unit}"
        mbps /= 1000
    string = f"{{:{fmt}}}".format(mbps)
    return f"{string} PB/s"


def latency_fmt(ms, fmt=".2f"):
    """Format latency with appropriate unit scaling (s, ms, µs, ns)."""
    assert ms >= 0
    if ms >= 1000:
        s = ms / 1000
        string = f"{{:{fmt}}}".format(s)
        return f"{string} s"
    elif ms >= 1:
        string = f"{{:{fmt}}}".format(ms)
        return f"{string} ms"
    elif ms >= 0.001:
        us = ms * 1000
        string = f"{{:{fmt}}}".format(us)
        return f"{string} µs"
    else:
        ns = ms * 1000000
        string = f"{{:{fmt}}}".format(ns)
        return f"{string} ns"


def iops_fmt(iops, fmt=".2f"):
    """Format IOPS with appropriate unit scaling (IO/s, KIO/s, MIO/s, GIO/s)."""
    assert iops >= 0
    for unit in ["IO/s", "KIO/s", "MIO/s", "GIO/s"]:
        if iops < 1000:
            string = f"{{:{fmt}}}".format(iops)
            return f"{string} {unit}"
        iops /= 1000
    string = f"{{:{fmt}}}".format(iops)
    return f"{string} TIO/s"
