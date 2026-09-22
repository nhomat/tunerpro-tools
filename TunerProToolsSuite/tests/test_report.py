import json

from tunerpro_tools.bin_file import BinFile
from tunerpro_tools.report import save_analysis_report_html, save_analysis_report_json


def test_save_analysis_report_json(tmp_path):
    bf = BinFile("mem", bytes(range(256)))
    stats = bf.compute_stats()
    output = tmp_path / "report.json"
    save_analysis_report_json("mem.bin", stats, output)
    data = json.loads(output.read_text())
    assert data["mode"] == "ANALYSE"
    assert data["stats"]["size"] == 256
    assert len(data["histogram"]) == 256


def test_save_analysis_report_html(tmp_path):
    bf = BinFile("mem", bytes(range(16)))
    stats = bf.compute_stats()
    output = tmp_path / "report.html"
    save_analysis_report_html("mem.bin", stats, output)
    html = output.read_text()
    assert "MODE: ANALYSE" in html
    assert "<table>" in html
