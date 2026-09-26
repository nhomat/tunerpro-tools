from tunerpro_tools.checksum import checksum_sum32, crc32, detect_checksum


def test_detects_real_crc32_trailer():
    payload = bytes(range(64)) * 3
    checksum = crc32(payload)
    data = payload + checksum.to_bytes(4, "big")

    detections = detect_checksum(data)
    matches = [d for d in detections if d.algorithm == "crc32"]
    assert matches
    assert matches[0].byte_order == "big"
    assert matches[0].value == checksum
    assert matches[0].zone_end == len(payload)


def test_detects_little_endian_trailer():
    payload = bytes(range(32))
    checksum = checksum_sum32(payload)
    data = payload + checksum.to_bytes(4, "little")

    detections = detect_checksum(data)
    matches = [d for d in detections if d.algorithm == "sum32"]
    assert matches
    assert matches[0].byte_order == "little"


def test_no_false_positive_on_random_trailing_bytes():
    # trailing bytes chosen so they do NOT match any algorithm's real
    # checksum of the preceding data - detection must come back empty,
    # not invent a match.
    payload = bytes(range(50))
    fake_trailer = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    data = payload + fake_trailer

    real_values = set()
    from tunerpro_tools.checksum import ALGORITHMS
    for algo in ALGORITHMS.values():
        real_values.add(algo.func(payload))
    fake_value_big = int.from_bytes(fake_trailer[-4:], "big")
    fake_value_little = int.from_bytes(fake_trailer[-4:], "little")
    assert fake_value_big not in real_values and fake_value_little not in real_values

    assert detect_checksum(data) == []


def test_1_byte_algorithms_not_reported_twice_for_both_byte_orders():
    payload = bytes(range(20))
    from tunerpro_tools.checksum import checksum_xor
    checksum = checksum_xor(payload)
    data = payload + bytes([checksum])

    detections = detect_checksum(data)
    xor_matches = [d for d in detections if d.algorithm == "xor"]
    assert len(xor_matches) == 1
