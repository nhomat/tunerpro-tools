# SAFETY.md

## Ce que fait cet outil

Map Optimizer Assistant a deux onglets, sur une zone de table lue dans
un fichier `.bin` :

### Onglet Lissage & detection (mode SIMULATION, lecture seule)

1. **Lissage** - reduit les ecarts brusques entre cellules voisines.
2. **Detection d'ecarts isoles** - signale une cellule qui jure avec ses
   voisines (souvent une erreur de saisie/transfert).

Cet onglet n'ecrit jamais rien ; les resultats sont un aperçu et un
export CSV facultatif.

### Onglet Tuning (mode MODIFICATION DE FICHIER, uniquement a l'ecriture)

Vous saisissez vous-meme des **points de reference** (ligne, colonne,
valeur cible) - vos propres valeurs, issues de votre banc, d'une
calibration de reference ou de la documentation constructeur. L'outil
**interpole** entre ces points pour remplir le reste de la table
(geometrie pure, meme principe que remplir une table a la main entre
quelques points connus). Il ne choisit jamais une valeur cible
lui-meme.

L'ecriture ne se produit que si vous cliquez explicitement sur "Ecrire
dans une copie...", apres confirmation dans une boite de dialogue
rappelant l'avertissement ci-dessous, et **toujours vers un nouveau
fichier** - le fichier source reste intact (refus explicite si vous
tentez de choisir le meme chemin, voir `patch.assert_safe_destination`).

## Ce que cet outil ne fait jamais, dans aucun onglet

- Il n'estime **ni la puissance, ni le couple, ni la richesse (AFR),
  ni la marge de cliquetis**. Ces grandeurs dependent de donnees
  capteur en temps reel (sonde a large bande, capteur de cliquetis,
  temperature des gaz d'echappement, charge moteur reelle) qui
  n'existent pas dans un fichier statique.
- Il ne choisit **jamais** lui-meme qu'une cellule devrait etre plus
  riche/pauvre ou avoir plus/moins d'avance "pour plus de puissance" -
  toute valeur qu'il produit vient soit du lissage de donnees
  existantes, soit de l'interpolation de valeurs que vous avez tapees.
- Il n'ecrit **jamais** dans le fichier source ouvert - uniquement,
  et sur demande explicite, dans une copie portant un nom different.

## Pourquoi ces limites existent

Determiner qu'une modification de calibration "n'endommagera rien" sur
un moteur reel necessite un banc de puissance, des capteurs en direct
et l'experience d'un tuner - aucune analyse hors ligne d'un fichier ne
peut fournir cette garantie. Presenter une suggestion generee
automatiquement comme prete a rouler serait a la fois faux et
dangereux : ce logiciel ne le fait pas, et aucune future version ne
devrait le faire sans un retour matériel reel en boucle.

## Mode

Cet outil fonctionne en mode **SIMULATION** (bandeau affiche dans son
interface) : aucune ecriture de fichier, aucune promesse de resultat
sur vehicule reel.
