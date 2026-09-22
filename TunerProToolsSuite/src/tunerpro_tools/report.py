"""HTML / JSON report generation for BIN Analyzer and friends."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .bin_file import ByteStats
from .config import APP_NAME, APP_VERSION


def analysis_report_dict(file_path: str | Path, stats: ByteStats) -> dict:
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "file": str(file_path),
        "mode": "ANALYSE",
        "stats": {
            "size": stats.size,
            "unique_values": stats.unique_values,
            "min": stats.minimum,
            "max": stats.maximum,
            "mean": stats.mean,
            "entropy": stats.entropy,
        },
        "histogram": list(stats.histogram),
    }


def save_analysis_report_json(file_path: str | Path, stats: ByteStats, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.write_text(json.dumps(analysis_report_dict(file_path, stats), indent=2), encoding="utf-8")
    return output_path


def save_analysis_report_html(file_path: str | Path, stats: ByteStats, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    histogram_rows = "\n".join(
        f"<tr><td>0x{i:02X}</td><td>{count}</td></tr>"
        for i, count in enumerate(stats.histogram)
        if count > 0
    )
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>BIN Analyzer - Rapport</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; background: #1e1e1e; color: #ddd; }}
table {{ border-collapse: collapse; margin-top: 1em; }}
th, td {{ border: 1px solid #444; padding: 4px 10px; }}
th {{ background: #2d2d2d; }}
.badge {{ display: inline-block; padding: 2px 8px; background: #3a5; border-radius: 4px; }}
</style>
</head>
<body>
<h1>BIN Analyzer &mdash; Rapport d'analyse</h1>
<p class="badge">MODE: ANALYSE</p>
<p>Fichier : {file_path}</p>
<p>Genere le : {datetime.now().isoformat(timespec='seconds')}</p>
<ul>
<li>Taille : {stats.size} octets</li>
<li>Valeurs uniques : {stats.unique_values}</li>
<li>Min / Max / Moyenne : {stats.minimum} / {stats.maximum} / {stats.mean:.2f}</li>
<li>Entropie : {stats.entropy:.4f} bits/octet</li>
</ul>
<h2>Histogramme des octets (valeurs non nulles)</h2>
<table>
<tr><th>Valeur</th><th>Occurrences</th></tr>
{histogram_rows}
</table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
