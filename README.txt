===================================================================
  PROJET : Planification d'Examens par Coloration de Graphes
  Niveau L2 Informatique — Théorie des Graphes
===================================================================

ORGANISATION DES FICHIERS
--------------------------
  graphe.py       — Partie 1 : construction et visualisation du graphe
  coloration.py   — Partie 2 : algorithmes Welsh-Powell et DSATUR
  affectation.py  — Partie 3 : affectation des salles, audit
  planning.py     — Partie 3 : tableau planning et export CSV
  main.py         — Point d'entrée principal (données d'exemple incluses)
  requirements.txt — Dépendances Python

INSTALLATION DES DÉPENDANCES
-----------------------------
  pip install -r requirements.txt

LANCEMENT
---------
  python main.py

FICHIERS GÉNÉRÉS
----------------
  graphe_non_colore.png  — Image du graphe de conflits brut
  graphe_colore.png      — Image du graphe avec créneaux colorés (PNG)
  planning.csv           — Planning final créneau × salle (CSV)

ADAPTATION À VOS DONNÉES
--------------------------
Modifiez les dictionnaires en haut de main.py :

  INSCRIPTIONS          — {code_UE: {liste étudiants}}
  UES_INFO              — Effectif, filière, labo requis, surveillant
  SALLES_DISPO          — Code, capacité, type (standard / labo)
  CONFLITS_SURVEILLANTS — Paires d'UE avec même surveillant
  INTERDICTIONS_JOUR    — Paires d'UE interdites le même jour

ALGORITHMES IMPLÉMENTÉS
------------------------
  Welsh-Powell  : tri par degré décroissant + attribution gloutonne
  DSATUR        : choix par saturation dynamique (généralement optimal)

Les deux algorithmes sont automatiquement comparés (créneaux + temps).
Le meilleur (moins de créneaux) est retenu pour le planning final.

CONTRAINTES RESPECTÉES
-----------------------
Obligatoires :
  ✓ Un étudiant ne compose qu'une UE par créneau
  ✓ Une salle = un seul examen par créneau
  ✓ Capacité salle >= effectif UE
  ✓ Pas de double affectation surveillant
  ✓ Laboratoire informatique si requis

Souhaitées :
  ✓ Espacement entre examens de même filière
  ✓ Priorité aux UE à grand effectif
  ✓ Interdictions explicites de co-journée
  ✓ Équilibre de la charge par créneau (audit)

===================================================================
