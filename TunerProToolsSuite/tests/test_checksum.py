import zlib

from tunerpro_tools.checksum import (
    ALGORITHMS,
    checksum_sum8,
    checksum_xor,
    compute_checksum,
    crc32,
)


def test_xor_checksum():
    assert checksum_xor(bytes([0x01, 0x02, 0x03])) == 0x00


def test_sum8_wraps_at_256():
    assert checksum_sum8(bytes([0xFF, 0x02])) == 0x01


def test_crc32_matches_stdlib():
    data = b"TunerPro Tools Suite"
    assert crc32(data) == (zlib.crc32(data) & 0xFFFFFFFF)


def test_all_registered_algorithms_run_without_error():
    data = bytes(range(64))
    for key in ALGORITHMS:
        result = compute_checksum(data, key, 0, len(data))
        assert result.computed_value >= 0


def test_compute_checksum_zone_bounds_validation():
    data = bytes(range(10))
    try:
        compute_checksum(data, "xor", 5, 2)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for invalid zone bounds")


def test_compute_checksum_reads_stored_value_and_compares():
    from tunerpro_tools.checksum import checksum_sum32

    data = bytearray(range(8))
    zone = bytes(data[0:4])
    stored = checksum_sum32(zone)
    data[4:8] = stored.to_bytes(4, "big")

    result = compute_checksum(bytes(data), "sum32", 0, 4, checksum_offset=4, byte_order="big")
    assert result.stored_value == stored
    assert result.matches is True


def test_compute_checksum_detects_mismatch():
    data = bytearray(range(8))
    data[4:8] = b"\x00\x00\x00\x00"
    result = compute_checksum(bytes(data), "sum32", 0, 4, checksum_offset=4, byte_order="big")
    assert result.matches is False


def test_unknown_algorithm_raises():
    try:
        compute_checksum(b"\x00", "not-a-real-algo", 0, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
