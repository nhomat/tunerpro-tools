# TUNERPRO_SETUP.md

Comment integrer TunerPro Tools Suite au menu **Custom Tools** de
TunerPro RT.

## Pre-requis

- Les executables sont compiles et installes (voir
  [`INSTALLATION.md`](INSTALLATION.md), etapes 3-4). Ils doivent exister
  dans `C:\TunerProToolsSuite\Tools\TunerPro_CustomTools\`.

## Ajouter un outil

1. Ouvrir TunerPro RT.
2. Menu **Tools > Custom Tools...**
3. Cliquer **Add**.
4. Renseigner les trois champs (voir le detail exact, outil par outil,
   dans [`TunerPro_CustomTools_Setup.txt`](../TunerPro_CustomTools_Setup.txt)) :
   - **Menu Text** : le nom affiche dans le menu (ex. `BIN Analyzer`)
   - **Tool Filename** : le chemin complet vers le `.exe`
     (ex. `C:\TunerProToolsSuite\Tools\TunerPro_CustomTools\BinAnalyzer.exe`)
   - **Keyboard Shortcut** : raccourci optionnel (ex. `Ctrl+1`)
5. Repeter pour chacun des 11 outils.
6. Fermer la boite de dialogue : le menu **Custom Tools** liste
   desormais chaque outil.

## Lancer un outil

Depuis TunerPro : **Tools > Custom Tools > <nom de l'outil>**, ou son
raccourci clavier. L'outil s'ouvre dans sa propre fenetre, comme un
programme externe independant - il ne communique pas avec TunerPro et
ne modifie rien pendant que TunerPro tourne.

## En cas de probleme

- **Rien ne se lance** : verifiez que le chemin dans *Tool Filename*
  correspond exactement a l'emplacement reel du `.exe` (voir
  `dir C:\TunerProToolsSuite\Tools\TunerPro_CustomTools\`).
- **Le raccourci clavier ne fonctionne pas** : un autre outil ou
  TunerPro utilise peut-etre deja cette combinaison ; changez-la dans
  Custom Tools.
- **L'outil s'ouvre puis se ferme immediatement** : lancez le `.exe`
  directement (double-clic dans l'Explorateur) pour voir un eventuel
  message d'erreur, et consultez `C:\TunerProToolsSuite\logs\`.
