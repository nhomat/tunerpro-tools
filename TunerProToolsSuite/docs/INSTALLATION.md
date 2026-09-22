# INSTALLATION.md

Guide pas a pas pour installer TunerPro Tools Suite sur **Windows**.

## 1. Installer Python (si necessaire)

1. Telecharger Python 3.10 ou plus recent depuis
   https://www.python.org/downloads/windows/
2. Lors de l'installation, cocher **"Add python.exe to PATH"**.
3. Verifier dans une invite de commandes :
   ```
   python --version
   ```

## 2. Installer les dependances

Depuis le dossier `TunerProToolsSuite\` :
```
python -m pip install -r requirements.txt
```
Cela installe PySide6 (interfaces), PyInstaller (compilation) et pytest
(tests).

## 3. Compiler les outils

```
build_all.bat
```
Ce script :
1. installe/verifie les dependances,
2. lance les tests automatises (`pytest tests -q`),
3. compile les 11 executables (10 outils + Dashboard) avec PyInstaller,
4. les place dans `dist\` (et une copie dans `TunerPro_CustomTools\`),
5. cree `TunerProToolsSuite-Windows.zip`.

> **Important** : PyInstaller ne fait pas de compilation croisee.
> `build_all.bat` doit etre execute **sur Windows** pour produire des
> `.exe` Windows. Execute sur Linux/macOS, PyInstaller produirait un
> executable natif de cette plateforme, pas un `.exe`.

## 4. Installer les .exe

```
install_tunerpro_tools.bat
```
Ce script copie les executables compiles vers
`C:\TunerProToolsSuite\Tools\TunerPro_CustomTools\`, cree l'arborescence
`Config\`, `Backups\`, `Reports\`, `Projects\`, `logs\`, et ajoute des
raccourcis sur le Bureau et dans le menu Demarrer. Il ecrit egalement
`uninstall_tunerpro_tools.bat` pour desinstaller proprement plus tard.

## 5. Configurer TunerPro

Ouvrir TunerPro RT, puis **Tools > Custom Tools > Add**.

## 6. Ajouter chaque Custom Tool

Suivre exactement [`TunerPro_CustomTools_Setup.txt`](../TunerPro_CustomTools_Setup.txt)
(a la racine du projet) : il donne le *Menu Text*, le *Tool Filename*
complet et un *Keyboard Shortcut* suggere pour chacun des 11 outils.

## 7. Tester les raccourcis

Dans TunerPro, ouvrir le menu **Custom Tools** et verifier que chaque
entree (BIN Analyzer, BIN Compare, ...) lance bien la fenetre
correspondante, et que le raccourci clavier configure fonctionne.

## 8. Ouvrir un BIN d'exemple

Lancer **BIN Analyzer** (directement ou depuis TunerPro) et ouvrir :
```
C:\TunerProToolsSuite\Projects\example_original.bin
```
(copie par `install_tunerpro_tools.bat` depuis `examples\`). Vous
devriez voir la taille (4096 octets), l'entropie et l'histogramme se
remplir.

## 9. Comparer deux fichiers

Lancer **BIN Compare**, selectionner :
- Original BIN : `example_original.bin`
- Modified BIN : `example_modified.bin`

et cliquer **Comparer** : l'outil doit signaler exactement 4
differences (voir `examples/example_manifest.json` pour le detail des
offsets et valeurs plantees).

## 10. Creer une premiere configuration de map

Dans **Map Viewer**, ouvrir `example_original.bin`, saisir :
- Offset : `0x100`, Lignes : `16`, Colonnes : `16`, Taille cellule : `1`

cliquer **Lire la map**, puis **Sauvegarder la config (JSON)** - ou
ouvrir **Map Database** pour l'enregistrer sous un nom (ex. "RPM") afin
de la retrouver plus tard.

## Desinstallation

```
uninstall_tunerpro_tools.bat
```
(cree automatiquement par `install_tunerpro_tools.bat` a cote de
lui-meme) supprime `C:\TunerProToolsSuite\` ainsi que les raccourcis.
