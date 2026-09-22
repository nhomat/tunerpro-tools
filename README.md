# TunerPro Tools

Outils hors ligne pour l'analyse et la simulation de fichiers de
calibration moteur (`.bin`), destines a completer
[TunerPro RT](https://www.tunerpro.net/) via son menu Custom Tools.

Deux projets independants, chacun compilable en `.exe` separement :

## [TunerProToolsSuite/](TunerProToolsSuite/)

La suite complete : BIN Analyzer, BIN Compare, Map Viewer, Calibration
Diff, Value Converter, Checksum Analyzer, Lambda AFR Calculator, BIN
Backup Manager, Map Database, Calibration Session, et un Dashboard qui
les lance tous. Voir son [README](TunerProToolsSuite/README.md) et son
dossier `docs/` (installation, guide utilisateur, securite).

## [TunerProMapOptimizer/](TunerProMapOptimizer/)

Outil complementaire avec deux fonctions :
- **Lissage & detection** - suggere un lissage et signale les cellules
  isolees dans une table (lecture seule).
- **Tuning (interpolation)** - interpole entre des points de reference
  saisis par l'utilisateur, avec ecriture optionnelle dans une copie du
  fichier (jamais l'original). Voir son
  [README](TunerProMapOptimizer/README.md) et
  [`docs/SAFETY.md`](TunerProMapOptimizer/docs/SAFETY.md).

## Principe commun aux deux projets

- Fonctionnement 100% hors ligne.
- Un fichier BIN original n'est jamais modifie automatiquement ; toute
  ecriture se fait dans une copie, apres confirmation explicite.
- Aucune estimation de puissance/couple/richesse/cliquetis : ces
  grandeurs dependent de donnees capteur reelles (banc, sonde large
  bande, capteur de cliquetis) qu'un fichier statique ne contient pas.
- Interface PySide6 (theme sombre), compilation Windows via PyInstaller
  (`build_all.bat` dans chaque dossier).
