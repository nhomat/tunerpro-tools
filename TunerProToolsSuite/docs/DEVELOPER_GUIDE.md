# DEVELOPER_GUIDE.md

## Architecture

```
TunerProToolsSuite/
  src/tunerpro_tools/
    config.py          # SuiteConfig: resolves Tools/Config/Backups/Reports/Projects/logs paths
    logging_utils.py    # per-tool logger writing to logs/<tool>.log
    bin_file.py          # BinFile: stats, entropy, search, hex dump (read-only)
    checksum.py          # XOR/SUM/CRC8/CRC16/CRC32 registry + compute_checksum()
    compare.py           # byte diff, neutral VariationLevel classification, CSV/HTML export
    converter.py         # HEX/DEC/BIN/intN conversions, little/big endian
    lambda_afr.py        # AFR<->Lambda, fuel profiles
    map_model.py         # MapDefinition, extract_map(), scale_value()/unscale_value()
    map_database.py      # SQLite-backed MapDefinition store
    backup_manager.py    # timestamped copy-based backups, restore
    session.py            # CalibrationSession (.tpsuite, gzip-compressed JSON)
    report.py             # HTML/JSON analysis reports
    theme.py               # dark QSS stylesheet
    app_base.py            # ToolWindow base QMainWindow + run_app()
    widgets/common.py      # BinFileDropField (drag&drop), mode_banner(), progress helpers
  tools/<tool_name>/main.py   # one PySide6 entry point per tool, each independently runnable
  config/default_config.json  # shortcuts, defaults
  build/tunerpro_tools.spec    # one PyInstaller spec building all 11 executables
  tests/                        # pytest, core library only (no GUI dependency for assertions)
  examples/generate_examples.py # synthetic example_original.bin / example_modified.bin
```

`src/tunerpro_tools` has **no PySide6 imports** except under
`widgets/`, so the core library is testable without a display and
reusable if a tool is ever reimplemented with a different UI layer.
Each `tools/*/main.py` inserts `src/` onto `sys.path` itself, so every
tool remains independently launchable (`python tools/bin_analyzer/main.py`)
and independently freezable by PyInstaller - there is no hidden
dependency between tools.

## Why PySide6 (not Tkinter / Electron)

- **Tkinter**: ships with Python, but its default look is dated and
  building drag&drop, a dark theme, tables, 2D charts and a 3D surface
  view with it would mean recreating what Qt already provides.
- **Electron/Node**: a second full runtime (Node + Chromium) to embed
  and maintain alongside Python, far heavier for an offline desktop
  tool than a single Python + Qt stack.
- **PySide6** (official Qt for Python bindings, LGPL): one language for
  both the analysis logic and the UI, native Windows rendering,
  built-in `QtCharts` (2D) and `QtDataVisualization` (3D surface), and
  PyInstaller support for freezing to a single `.exe`.

## Running a tool during development

```bash
pip install -r requirements.txt
python tools/bin_analyzer/main.py
```

## Tests

```bash
python -m pytest tests -q
```

Tests cover the core library exhaustively (byte stats/entropy/search,
every checksum algorithm, diff/classification, converter round-trips,
map extraction/scaling, backup/restore semantics, the SQLite map store,
`.tpsuite` session round-trip, report generation) plus an end-to-end
check that `examples/generate_examples.py` produces files where BIN
Compare finds exactly the planted differences and Checksum Analyzer
correctly flags the modified file's checksum mismatch. GUI smoke-testing
(each tool window constructs and responds to its core actions without
raising) was run manually with `QT_QPA_PLATFORM=offscreen` during
development; it is not part of the automated suite because it requires
a PySide6 installation, which `requirements.txt` already provides but
which the test command above does not assume is display-less-safe on
every platform.

## Building the executables

```bash
build_all.bat
```

This runs `pytest`, regenerates the example files, then invokes:

```bash
python -m PyInstaller --distpath dist --workpath build\pyinstaller_work build\tunerpro_tools.spec
```

`build/tunerpro_tools.spec` defines one `Analysis`/`EXE` pair per tool
(11 total, including Dashboard), all `--onefile`-equivalent, windowed
(no console), each depending only on its own `tools/<name>/main.py` and
the shared `src/tunerpro_tools` package.

### Cross-platform limitation (read this before assuming a build worked)

**PyInstaller does not cross-compile.** It packages the interpreter and
libraries of the machine it runs on. This repository's automated
development/test environment is Linux; running `build/tunerpro_tools.spec`
there was used **only to validate that the spec itself is correct**
(all 11 executables built and one was smoke-launched successfully) - it
produced Linux ELF binaries, not Windows `.exe` files. **Real `.exe`
artifacts must be produced by running `build_all.bat` (or the
PyInstaller command above) on an actual Windows machine, or a Windows
CI runner.** Do not treat a Linux-built binary as a deliverable `.exe`.

## Adding a new checksum algorithm

Add a function `(data: bytes) -> int` in `checksum.py` and register a
`ChecksumAlgorithm` entry in `ALGORITHMS`; Checksum Analyzer's dropdown
picks it up automatically - no other file needs to change.

## Adding a new tool

1. Create `tools/<new_tool>/main.py`.
2. Insert `src/` onto `sys.path` (copy the three-line snippet from an
   existing tool).
3. Subclass `tunerpro_tools.app_base.ToolWindow`, pick a mode
   (`ANALYSE` / `SIMULATION` / `MODIFICATION DE FICHIER`), build your
   UI in `self.content_layout`.
4. Call `tunerpro_tools.app_base.run_app(YourWindow)` from `main()`.
5. Add it to `TOOLS` in `tools/dashboard/main.py`, to the `TOOLS` list
   in `build/tunerpro_tools.spec`, and document it in
   `TunerPro_CustomTools_Setup.txt` and `docs/USER_GUIDE.md`.

## Logging

Every tool calls `tunerpro_tools.logging_utils.get_tool_logger(name)`
and `log_operation(logger, operation, file_used, error)`, writing to
`logs/<name>.log` (date, tool, file, operation, error - never anything
beyond that).
