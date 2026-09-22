# USER_GUIDE.md

Guide d'utilisation de chaque outil. Tous les outils sont hors ligne,
en theme sombre, acceptent le glisser-deposer d'un fichier `.bin` sur
leur champ de fichier, et ferment avec **Ctrl+Q**.

## Dashboard

Fenetre unique listant les 10 outils. Cliquer sur un bouton lance
l'outil correspondant comme processus independant (le `.exe` s'il
existe a cote du Dashboard, sinon son `main.py` en developpement).

## BIN Analyzer (mode ANALYSE)

1. Glisser un `.bin` sur le champ du haut (ou **Ctrl+O**).
2. Onglet **Statistiques** : taille, nombre d'octets, valeurs uniques,
   min/max/moyenne, entropie, histogramme (regroupe par 16 valeurs).
   Boutons **Save Analysis Report** (HTML ou JSON).
3. Onglet **Vue hexadecimale** : dump hexa + ASCII, **Ctrl+G** pour
   sauter a un offset (hexadecimal et decimal affiches simultanement).
4. Onglet **Recherche** : sequence d'octets (hex, ex. `DEADBEEF`) ou
   valeur 8/16/32-bit signee/non signee. Double-clic sur un resultat
   pour sauter a son offset dans la vue hexadecimale. Export CSV des
   resultats.

## BIN Compare (mode ANALYSE)

1. Charger **Original BIN** et **Modified BIN**.
2. **Comparer** : le resume affiche les tailles et le nombre de
   differences.
3. Onglet **Differences** : tableau Offset / Original / Modified /
   Difference. Filtre par delta minimum, navigation Precedent/Suivant,
   export CSV et HTML.
4. Onglet **Vue hexadecimale** : original et modifie cote a cote autour
   de l'offset selectionne.
5. Onglet **Vue graphique** : nuage de points offset vs delta, pour
   reperer visuellement les zones modifiees.

Aucun fichier n'est modifie par cet outil.

## Map Viewer (mode ANALYSE)

1. Charger un `.bin`.
2. Definir : offset, lignes, colonnes, taille de cellule (1/2/4
   octets), endianess, signe, facteur et offset mathematique
   (`valeur reelle = brute x facteur + offset`).
3. **Lire la map** remplit trois vues : **Tableau** (brut + converti),
   **Graphique 2D** (une courbe par ligne) et **Surface 3D**
   (necessite un affichage graphique standard ; indisponible en mode
   d'affichage "offscreen" utilise par certains environnements
   automatises).
4. **Sauvegarder/Charger la config (JSON)** pour reutiliser une
   definition de map.

## Lambda AFR Calculator (mode SIMULATION)

Conversions **theoriques** AFR <-> Lambda pour plusieurs carburants
(essence, E85, E100, diesel, methanol). Un bandeau rappelle que les
valeurs reelles dependent du carburant et du contexte moteur. Un
tableau affiche des points de conversion courants (Lambda 0.80 a 1.20).

## Calibration Diff (mode ANALYSE)

1. Charger une calibration originale et une modifiee.
2. Definir la zone (offset, lignes, colonnes, taille de cellule,
   endianess, signe) puis **Comparer la zone**.
3. Resume : cellules modifiees, variation moyenne/maximale/minimale.
4. Heatmap colorée par cellule, avec legende **faible variation /
   variation moderee / variation importante** - jamais de qualificatif
   de securite.

## Value Converter (mode ANALYSE)

Saisir une valeur (hex/dec/bin) et son endianess : le tableau affiche
simultanement HEX/DEC/BIN pour UINT8, INT8, UINT16, INT16, UINT32,
INT32 (les types hors plage affichent "hors plage").

## Checksum Analyzer (mode ANALYSE)

1. Charger un `.bin`.
2. Choisir l'algorithme (XOR, SUM 8/16/32, CRC8, CRC16-CCITT, CRC32) et
   la zone (debut/fin).
3. Optionnel : cocher **Comparer avec une valeur stockee**, indiquer
   son offset et son ordre d'octets pour verifier la correspondance.

Cet outil ne calcule et ne compare que des checksums - il n'en ecrit
jamais dans le fichier.

## BIN Backup Manager (mode MODIFICATION DE FICHIER)

1. Glisser le fichier a sauvegarder, choisir la categorie
   (original/modified), **Creer la sauvegarde** : une copie horodatee
   est deposee dans `Backups/original/` ou `Backups/modified/` -
   l'original n'est jamais touche.
2. La liste des sauvegardes existantes se rafraichit automatiquement.
3. **Restore Original...** copie une sauvegarde vers un nouvel
   emplacement choisi ; l'operation est refusee si le fichier de
   destination existe deja (pour eviter tout ecrasement accidentel).

## Map Database (mode ANALYSE)

Base SQLite locale de configurations de maps nommees (RPM, Load,
Ignition, Fuel, Temperature ou tout autre nom). Chaque entree est
saisie et validee par vous - aucune map n'est jamais devinee
automatiquement a partir d'un fichier BIN.

## Calibration Session (mode ANALYSE)

Projet `.tpsuite` regroupant BIN original/modifie, maps utilisees,
notes libres et historique horodate des actions. **Nouveau / Ouvrir /
Enregistrer** (**Ctrl+O** / **Ctrl+S**).
