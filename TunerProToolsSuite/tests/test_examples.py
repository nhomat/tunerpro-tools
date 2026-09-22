import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from generate_examples import generate  # noqa: E402

from tunerpro_tools.bin_file import BinFile
from tunerpro_tools.checksum import compute_checksum
from tunerpro_tools.compare import compare_bytes
from tunerpro_tools.map_model import MapDefinition, extract_map


def test_generate_is_deterministic(tmp_path):
    manifest_a = generate(tmp_path / "a")
    manifest_b = generate(tmp_path / "b")
    assert manifest_a == manifest_b
    assert (tmp_path / "a" / "example_original.bin").read_bytes() == (
        tmp_path / "b" / "example_original.bin"
    ).read_bytes()


def test_bin_compare_finds_exactly_the_planted_differences(tmp_path):
    manifest = generate(tmp_path)
    original = (tmp_path / "example_original.bin").read_bytes()
    modified = (tmp_path / "example_modified.bin").read_bytes()

    summary = compare_bytes(original, modified)
    found_offsets = sorted(d.offset for d in summary.differences)
    expected_offsets = sorted(d["offset"] for d in manifest["planted_differences"])
    assert found_offsets == expected_offsets

    by_offset = {d.offset: d for d in summary.differences}
    for planted in manifest["planted_differences"]:
        assert by_offset[planted["offset"]].delta == planted["delta"]


def test_search_needle_found_at_documented_offset(tmp_path):
    manifest = generate(tmp_path)
    bf = BinFile.load(tmp_path / "example_original.bin")
    matches = bf.search_bytes(bytes.fromhex(manifest["search_needle_hex"]))
    assert [m.offset for m in matches] == [manifest["search_needle_offset"]]


def test_checksum_matches_on_original_and_mismatches_on_modified(tmp_path):
    manifest = generate(tmp_path)
    original = (tmp_path / "example_original.bin").read_bytes()
    modified = (tmp_path / "example_modified.bin").read_bytes()

    zone_start, zone_end = manifest["checksum_zone"]
    result_original = compute_checksum(
        original, manifest["checksum_algorithm"], zone_start, zone_end,
        checksum_offset=manifest["checksum_offset"], byte_order=manifest["checksum_byte_order"],
    )
    assert result_original.matches is True

    result_modified = compute_checksum(
        modified, manifest["checksum_algorithm"], zone_start, zone_end,
        checksum_offset=manifest["checksum_offset"], byte_order=manifest["checksum_byte_order"],
    )
    assert result_modified.matches is False


def test_rpm_and_fuel_maps_extract_cleanly(tmp_path):
    generate(tmp_path)
    data = (tmp_path / "example_original.bin").read_bytes()

    rpm_definition = MapDefinition.from_dict(
        json.loads((tmp_path / "example_map_rpm.json").read_text())
    )
    rpm_map = extract_map(data, rpm_definition)
    assert len(rpm_map.raw) == rpm_definition.rows
    assert len(rpm_map.raw[0]) == rpm_definition.columns

    fuel_definition = MapDefinition.from_dict(
        json.loads((tmp_path / "example_map_fuel.json").read_text())
    )
    fuel_map = extract_map(data, fuel_definition)
    assert len(fuel_map.raw) == fuel_definition.rows
