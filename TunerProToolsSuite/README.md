# TunerPro Tools Suite

Suite d'outils hors ligne pour l'**analyse** et la **simulation** de
fichiers de calibration moteur (`.bin`), pensee pour completer
[TunerPro RT](https://www.tunerpro.net/) via son menu *Custom Tools*.

> **Ce projet ne modifie jamais un fichier BIN original automatiquement.**
> Voir [`docs/SAFETY.md`](docs/SAFETY.md).

## Outils inclus

| Outil | Dossier | Role |
|---|---|---|
| Dashboard | `tools/dashboard` | Lance les 10 outils depuis une seule fenetre |
| BIN Analyzer | `tools/bin_analyzer` | Stats, entropie, hexadecimal, recherche, rapport HTML/JSON |
| BIN Compare | `tools/bin_compare` | Diff octet par octet entre deux BIN, export CSV/HTML |
| Map Viewer | `tools/map_viewer` | Tableau / graphique 2D / surface 3D d'une map |
| Lambda AFR Calculator | `tools/lambda_afr_calculator` | Conversions AFR <-> Lambda (theoriques) |
| Calibration Diff | `tools/calibration_diff` | Heatmap de variation entre deux calibrations |
| Value Converter | `tools/value_converter` | HEX / DEC / BIN / UINT8..INT32, little/big endian |
| Checksum Analyzer | `tools/checksum_analyzer` | XOR / SUM / CRC8 / CRC16 / CRC32 |
| BIN Backup Manager | `tools/backup_manager` | Sauvegardes horodatees, restauration |
| Map Database | `tools/map_database` | Base locale SQLite de configurations de maps |
| Calibration Session | `tools/session_manager` | Projets `.tpsuite` (BIN, maps, notes, historique) |

## Architecture

```
TunerProToolsSuite/
  src/tunerpro_tools/   # bibliotheque coeur, sans dependance GUI (sauf widgets/)
  tools/<nom_outil>/    # un main.py par outil, compilable en .exe independant
  config/               # configuration centralisee (default_config.json)
  docs/                 # documentation complete
  build/                # spec PyInstaller
  tests/                # tests automatises (pytest)
  examples/             # BIN fictifs + generateur
```

Technologie : **Python 3.10+ / PySide6** pour les interfaces, compilees
en `.exe` Windows avec **PyInstaller**. PySide6 a ete retenu plutot que
Tkinter (rendu trop dat pour "interface moderne") ou Electron/Node
(empreinte disque et memoire bien plus lourde pour un outil hors ligne,
et deuxieme runtime a maintenir a cote de Python) : un seul langage
suffit pour la logique d'analyse ET l'interface, avec un rendu natif
correct sous Windows.

## Demarrage rapide (developpement)

```bash
pip install -r requirements.txt
python tools/dashboard/main.py
```

## Documentation

- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) - installation pas a pas
- [`docs/TUNERPRO_SETUP.md`](docs/TUNERPRO_SETUP.md) - configuration du menu Custom Tools
- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) - guide d'utilisation de chaque outil
- [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) - architecture, build, tests
- [`docs/SAFETY.md`](docs/SAFETY.md) - regles de securite (ANALYSE / SIMULATION / MODIFICATION)

## Tests

```bash
python -m pytest tests -q
```
