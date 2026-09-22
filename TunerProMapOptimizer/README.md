# Map Optimizer Assistant

Outil hors ligne complementaire a [TunerPro Tools Suite], destine a
TunerPro RT via son menu Custom Tools.

Deux onglets :

- **Lissage & detection** (lecture seule) - suggere un lissage des
  cellules et signale les ecarts isoles (souvent une erreur de saisie).
- **Tuning (interpolation)** - vous saisissez des points de reference
  (ligne/colonne/valeur cible) issus de votre propre expertise ou banc,
  et l'outil interpole le reste de la table. Peut ecrire le resultat
  dans une **copie** du fichier (jamais l'original), apres confirmation.

**Aucune valeur cible n'est jamais choisie par l'outil, et le fichier
source n'est jamais modifie** - il n'evalue ni la puissance, ni le
couple, ni la richesse, ni le risque de cliquetis. Voir
[`docs/SAFETY.md`](docs/SAFETY.md) pour le detail et pourquoi.

## Demarrage rapide (developpement)

```bash
pip install -r requirements.txt
python tool/main.py
```

## Tests

```bash
python -m pytest tests -q
```

## Compiler le .exe (sur Windows)

```
build_all.bat
```
Produit `dist\MapOptimizer.exe`. PyInstaller ne fait pas de compilation
croisee : ce script doit tourner sur Windows pour produire un `.exe`
Windows.

## Ajouter a TunerPro

Voir [`docs/TUNERPRO_CUSTOM_TOOL_SETUP.txt`](docs/TUNERPRO_CUSTOM_TOOL_SETUP.txt).

## Architecture

```
src/map_optimizer/
  bin_file.py       # lecture seule d'un .bin
  map_model.py       # MapDefinition + extraction de grille
  optimizer.py        # lissage, detection d'ecarts isoles, interpolation de points cibles
  patch.py             # seul module qui ecrit des octets - toujours vers une copie
  theme.py / widgets/  # interface PySide6 (theme sombre, drag & drop)
tool/main.py           # fenetre principale (onglets Lissage / Tuning), point d'entree PyInstaller
tests/                 # pytest sur optimizer.py, map_model.py et patch.py
build/map_optimizer.spec  # spec PyInstaller
```
