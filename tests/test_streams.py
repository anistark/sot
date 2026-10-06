import sot


def test_braille_stream():
    stream = sot.BrailleStream(3, 1, 0.0, 100.0)

    stream.add_value(10.0)
    assert stream.graph == ["  ⢀"]

    stream.add_value(30.0)
    assert stream.graph == ["  ⣠"]

    stream.add_value(60.0)
    assert stream.graph == [" ⢀⣴"]

    stream.add_value(90.0)
    assert stream.graph == [" ⣠⣾"]


def test_braille_stream_upside_down():
    stream = sot.BrailleStream(3, 1, 0.0, 100.0, flipud=True)

    stream.add_value(10.0)
    assert stream.graph == ["  ⠈"]

    stream.add_value(30.0)
    assert stream.graph == ["  ⠙"]

    stream.add_value(60.0)
    assert stream.graph == [" ⠈⠻"]

    stream.add_value(90.0)
    assert stream.graph == [" ⠙⢿"]


def test_braille_stream_tall():
    stream = sot.BrailleStream(3, 4, 0.0, 100.0)

    stream.add_value(43.0)
    assert stream.graph == ["   ", "   ", "  ⢰", "  ⢸"]

    stream.add_value(10.0)
    assert stream.graph == ["   ", "   ", "  ⡆", "  ⣧"]

    stream.add_value(100.0)
    assert stream.graph == ["  ⢸", "  ⢸", " ⢰⢸", " ⢸⣼"]

    stream.add_value(76.0)
    assert stream.graph == ["  ⣇", "  ⣿", " ⡆⣿", " ⣧⣿"]

    stream.add_value(0.0)
    assert stream.graph == [" ⢸⡀", " ⢸⡇", "⢰⢸⡇", "⢸⣼⡇"]


def test_blockchar_stream():
    stream = sot.BlockCharStream(5, 1, 0.0, 100.0)

    stream.add_value(10.0)
    assert stream.graph == ["    ▁"]

    stream.add_value(30.0)
    assert stream.graph == ["   ▁▃"]

    stream.add_value(60.0)
    assert stream.graph == ["  ▁▃▅"]

    stream.add_value(100.0)
    assert stream.graph == [" ▁▃▅█"]

    stream.add_value(0.0)
    assert stream.graph == ["▁▃▅█ "]


def test_blockchar_stream_tall():
    stream = sot.BlockCharStream(3, 4, 0.0, 100.0)

    stream.add_value(10.0)
    assert stream.graph == ["   ", "   ", "   ", "  ▄"]

    stream.add_value(30.0)
    assert stream.graph == ["   ", "   ", "  ▂", " ▄█"]

    stream.add_value(60.0)
    assert stream.graph == ["   ", "  ▄", " ▂█", "▄██"]

    stream.add_value(100.0)
    assert stream.graph == ["  █", " ▄█", "▂██", "███"]

    stream.add_value(0.0)
    assert stream.graph == [" █ ", "▄█ ", "██ ", "██ "]


def test_blockchar_stream_upside_down():
    stream = sot.BlockCharStream(3, 2, 0.0, 100.0, flipud=True)

    stream.add_value(25.0)
    assert stream.graph == ["  ▀", "   "]

    stream.add_value(100.0)
    assert stream.graph == [" ▀█", "  █"]


def test_blockchar_stream_resize():
    stream = sot.BlockCharStream(3, 1, 0.0, 100.0)
    for value in (10.0, 60.0, 100.0):
        stream.add_value(value)

    stream.reset_width(5)
    assert stream.graph == ["  ▁▅█"]

    stream.reset_width(2)
    assert stream.graph == ["▅█"]

    stream.reset_height(2)
    assert stream.graph == ["▂█", "██"]
    assert stream.values == [60.0, 100.0]


def test_blockchar_stream_clamps_out_of_range():
    stream = sot.BlockCharStream(2, 1, 0.0, 100.0)
    stream.add_value(250.0)
    stream.add_value(-5.0)
    assert stream.graph == ["█ "]
