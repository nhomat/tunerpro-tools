import math

from tunerpro_tools.bin_file import BinFile


def test_load_and_size(tmp_path):
    path = tmp_path / "sample.bin"
    path.write_bytes(bytes([0, 1, 2, 3, 255]))
    bf = BinFile.load(path)
    assert bf.size == 5
    assert bf.data == bytes([0, 1, 2, 3, 255])


def test_stats_uniform_bytes_have_zero_entropy():
    bf = BinFile("mem", bytes([42] * 100))
    stats = bf.compute_stats()
    assert stats.size == 100
    assert stats.unique_values == 1
    assert stats.minimum == 42
    assert stats.maximum == 42
    assert stats.mean == 42
    assert stats.entropy == 0.0
    assert stats.histogram[42] == 100


def test_stats_max_entropy_for_uniform_distribution():
    data = bytes(range(256)) * 4
    bf = BinFile("mem", data)
    stats = bf.compute_stats()
    assert stats.unique_values == 256
    assert math.isclose(stats.entropy, 8.0, rel_tol=1e-9)


def test_empty_file_stats():
    bf = BinFile("mem", b"")
    stats = bf.compute_stats()
    assert stats.size == 0
    assert stats.entropy == 0.0


def test_search_bytes_finds_all_occurrences():
    bf = BinFile("mem", b"\x00\xAA\xBB\x00\xAA\xBB\xAA\xBB")
    matches = bf.search_bytes(b"\xAA\xBB")
    assert [m.offset for m in matches] == [1, 4, 6]


def test_search_bytes_empty_needle_returns_nothing():
    bf = BinFile("mem", b"\x00\x01")
    assert bf.search_bytes(b"") == []


def test_search_value_uint16_little_endian():
    # value 0x1234 little-endian encodes as 34 12
    bf = BinFile("mem", b"\x00\x34\x12\x00")
    matches = bf.search_value(0x1234, width=2, signed=False, byte_order="little")
    assert [m.offset for m in matches] == [1]


def test_search_value_int8_signed():
    bf = BinFile("mem", bytes([0x00, 0xFF, 0x01]))  # 0xFF == -1 signed
    matches = bf.search_value(-1, width=1, signed=True)
    assert [m.offset for m in matches] == [1]


def test_read_at_respects_endianness_and_sign():
    bf = BinFile("mem", b"\xFF\xFF")
    assert bf.read_at(0, width=2, signed=False, byte_order="little") == 0xFFFF
    assert bf.read_at(0, width=2, signed=True, byte_order="little") == -1


def test_read_at_out_of_range_raises():
    bf = BinFile("mem", b"\x01")
    try:
        bf.read_at(0, width=4)
    except IndexError:
        pass
    else:
        raise AssertionError("expected IndexError")


def test_hex_dump_format():
    bf = BinFile("mem", bytes(range(16)))
    dump = bf.hex_dump()
    assert dump.startswith("00000000  00 01 02")
    assert "|" in dump
