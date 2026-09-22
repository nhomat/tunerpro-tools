# SAFETY.md - Regles de securite

## Trois modes, toujours distincts

Chaque outil affiche en permanence, en haut de sa fenetre, une bannière
indiquant son mode :

- **ANALYSE** - lecture seule (BIN Analyzer, BIN Compare, Map Viewer,
  Calibration Diff, Checksum Analyzer, Map Database, Calibration
  Session, Value Converter).
- **SIMULATION** - calculs theoriques qui ne touchent a aucun fichier
  (Lambda AFR Calculator).
- **MODIFICATION DE FICHIER** - operations qui ecrivent sur le disque
  (BIN Backup Manager). Ces outils affichent en plus
  l'avertissement suivant :

  > "Cette modification est experimentale. Verifiez la compatibilite
  > du fichier, du calculateur et du materiel avant toute utilisation
  > reelle."

## Ce que la suite ne fait jamais

- **Ne jamais ecraser un fichier BIN original.** BIN Backup Manager ne
  copie que vers `Backups/original/` ou `Backups/modified/`, avec un
  nom horodate ; `restore_original()` refuse d'ecraser un fichier deja
  present a la destination (`FileExistsError`).
- **Ne jamais ecrire un checksum recalcule dans un fichier
  automatiquement.** Checksum Analyzer ne fait que comparer une valeur
  calculee a une valeur stockee ; aucune fonction de la suite n'ecrit
  un checksum dans un BIN.
- **Ne jamais inventer une map a partir du contenu d'un BIN.** Map
  Database et Map Viewer n'enregistrent que des configurations
  explicitement saisies par l'utilisateur. Si une detection
  heuristique est ajoutee un jour, elle devra afficher la mention
  `"Probable map - validation manuelle necessaire."`
  (`tunerpro_tools.map_model.PROBABLE_MAP_NOTICE`) et ne jamais etre
  presentee comme certaine.
- **Ne jamais qualifier une modification de "sure", "dangereuse",
  "bonne" ou "mauvaise".** Calibration Diff utilise exclusivement les
  libelles neutres *faible variation*, *variation moderee*, *variation
  importante* (`tunerpro_tools.compare.VariationLevel`).
- **Ne jamais presenter une calibration generee comme prete a etre
  flashee sur un moteur reel.** Aucun outil de la suite n'ecrit de
  calibration "finale" ; tout export reste un rapport d'analyse
  (HTML/JSON/CSV) ou une copie de sauvegarde.

## Donnees d'exemple

Les fichiers `examples/example_original.bin` et
`examples/example_modified.bin` sont generes par
`examples/generate_examples.py` a partir d'un generateur pseudo-aleatoire
a graine fixe. Ce sont des octets synthetiques : **ils ne proviennent
d'aucun vehicule reel et ne representent aucune calibration reelle.**

## Journalisation

Chaque outil ecrit dans `logs/<outil>.log` : date, outil, fichier
utilise, operation, erreur eventuelle (`tunerpro_tools.logging_utils`).
Aucune information personnelle non necessaire n'est enregistree - seuls
des chemins de fichiers et des noms d'operations.

## Utilisation hors ligne

Aucun outil de la suite n'effectue d'appel reseau. Toute l'analyse,
comparaison, conversion et sauvegarde se fait localement.
