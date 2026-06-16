"""
main.py — Point d'entrée principal du projet.

Lance l'ensemble du pipeline :
  1. Construction du graphe de conflits
  2. Coloration (Welsh-Powell et DSATUR)
  3. Affectation des salles
  4. Rapport d'audit
  5. Génération et export du planning

Un jeu de données exemple est fourni pour illustrer chaque partie du projet.
Modifiez les dictionnaires INSCRIPTIONS, SALLES_DISPO et UES_INFO pour
adapter au contexte réel de votre établissement.
"""

from graphe import GrapheConflits
from coloration import welsh_powell, dsatur, comparer_algorithmes, afficher_rapport_coloration
from affectation import Affectation, Salle, UEInfo
from planning import Planning


# ===========================================================================
# DONNÉES D'EXEMPLE
# Adaptez ces données à votre établissement.
# ===========================================================================

# Inscriptions : {code_UE: ensemble d'identifiants étudiants}
INSCRIPTIONS: dict[str, set] = {
    "MATH101":  {"E01", "E02", "E03", "E04", "E05", "E06", "E07"},
    "INFO102":  {"E02", "E03", "E08", "E09", "E10", "E11"},
    "PHYS103":  {"E01", "E04", "E05", "E12", "E13", "E14", "E15"},
    "ALGO104":  {"E08", "E09", "E10", "E16", "E17"},
    "STAT105":  {"E01", "E02", "E06", "E07", "E18", "E19"},
    "SYS106":   {"E11", "E16", "E17", "E20", "E21", "E22"},
    "BDD107":   {"E03", "E09", "E10", "E18", "E23"},
    "NET108":   {"E04", "E12", "E14", "E20", "E21", "E24"},
    "IA109":    {"E05", "E08", "E11", "E16", "E22", "E25"},
    "PROJ110":  {"E06", "E13", "E15", "E19", "E23", "E24"},
}

# Informations sur chaque UE
UES_INFO: dict[str, UEInfo] = {
    "MATH101": UEInfo("MATH101", nb_etudiants=7,  filiere="Tronc Commun",   necessite_labo=False, surveillant="Prof_Martin"),
    "INFO102": UEInfo("INFO102", nb_etudiants=6,  filiere="Informatique",   necessite_labo=True,  surveillant="Prof_Dupont"),
    "PHYS103": UEInfo("PHYS103", nb_etudiants=7,  filiere="Tronc Commun",   necessite_labo=False, surveillant="Prof_Leblanc"),
    "ALGO104": UEInfo("ALGO104", nb_etudiants=5,  filiere="Informatique",   necessite_labo=False, surveillant="Prof_Dupont"),
    "STAT105": UEInfo("STAT105", nb_etudiants=6,  filiere="Mathématiques",  necessite_labo=False, surveillant="Prof_Martin"),
    "SYS106":  UEInfo("SYS106",  nb_etudiants=6,  filiere="Informatique",   necessite_labo=True,  surveillant="Prof_Bernard"),
    "BDD107":  UEInfo("BDD107",  nb_etudiants=5,  filiere="Informatique",   necessite_labo=True,  surveillant="Prof_Dupont"),
    "NET108":  UEInfo("NET108",  nb_etudiants=6,  filiere="Réseaux",        necessite_labo=False, surveillant="Prof_Bernard"),
    "IA109":   UEInfo("IA109",   nb_etudiants=6,  filiere="Informatique",   necessite_labo=True,  surveillant="Prof_Durand"),
    "PROJ110": UEInfo("PROJ110", nb_etudiants=6,  filiere="Transversal",    necessite_labo=False, surveillant="Prof_Durand"),
}

# Salles disponibles
SALLES_DISPO: list[Salle] = [
    Salle("A101",  capacite=30, est_labo=False),
    Salle("A102",  capacite=25, est_labo=False),
    Salle("B201",  capacite=20, est_labo=False),
    Salle("LABO1", capacite=25, est_labo=True),
    Salle("LABO2", capacite=20, est_labo=True),
]

# Contraintes de surveillants : même enseignant → ajout d'un conflit
# (Prof_Dupont surveille INFO102, ALGO104, BDD107 — ils ne peuvent être simultanés)
CONFLITS_SURVEILLANTS: list[tuple] = [
    ("INFO102", "ALGO104"),
    ("INFO102", "BDD107"),
    ("ALGO104", "BDD107"),
    ("SYS106",  "NET108"),   # Prof_Bernard
    ("IA109",   "PROJ110"),  # Prof_Durand
    ("MATH101", "STAT105"),  # Prof_Martin
]

# Interdictions de même jour (contrainte souhaitée)
INTERDICTIONS_JOUR: set = {
    ("MATH101", "STAT105"),  # Trop proche pour les étudiants de maths
}


# ===========================================================================
# PIPELINE PRINCIPAL
# ===========================================================================

def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║  PLANIFICATION D'EXAMENS PAR COLORATION DE GRAPHES     ║")
    print("║  Projet L2 Informatique — Théorie des Graphes           ║")
    print("╚" + "═" * 58 + "╝\n")

    # -----------------------------------------------------------------------
    # PARTIE 1 — Construction du graphe
    # -----------------------------------------------------------------------
    print("━" * 60)
    print("  PARTIE 1 — Construction du graphe de conflits")
    print("━" * 60)

    ues = list(INSCRIPTIONS.keys())
    graphe = GrapheConflits(ues)

    # Conflits issus des inscriptions communes
    print("\n  Construction depuis les inscriptions étudiantes...")
    graphe.construire_depuis_inscriptions(INSCRIPTIONS)

    # Conflits supplémentaires : même surveillant
    print("  Ajout des contraintes de surveillants...")
    for ue1, ue2 in CONFLITS_SURVEILLANTS:
        graphe.ajouter_arete(ue1, ue2)

    # Affichage des statistiques
    graphe.afficher_stats()
    graphe.afficher_liste()

    # -----------------------------------------------------------------------
    # PARTIE 2 — Coloration et comparaison
    # -----------------------------------------------------------------------
    print("\n" + "━" * 60)
    print("  PARTIE 2 — Algorithmes de coloration")
    print("━" * 60)

    print("\n  Exécution de Welsh-Powell et DSATUR...")
    resultats = comparer_algorithmes(graphe, nb_repetitions=50)
    afficher_rapport_coloration(resultats)

    # Sélection du meilleur algorithme (moins de créneaux)
    meilleur_algo = min(resultats, key=lambda k: resultats[k]["nb_creneaux"])
    coloration_finale = resultats[meilleur_algo]["coloration"]
    print(f"\n  → Algorithme retenu : {meilleur_algo} "
          f"({resultats[meilleur_algo]['nb_creneaux']} créneaux)")

    # -----------------------------------------------------------------------
    # Visualisation du graphe (non coloré)
    # -----------------------------------------------------------------------
    print("\n  Génération du graphe de conflits (non coloré)...")
    graphe.visualiser(
        titre="Graphe de Conflits — Vue structurelle",
        fichier="graphe_non_colore.png"
    )

    # -----------------------------------------------------------------------
    # Visualisation du graphe coloré
    # -----------------------------------------------------------------------
    print("  Génération du graphe coloré...")
    graphe.visualiser(
        coloration=coloration_finale,
        titre=f"Graphe Coloré — {meilleur_algo} "
              f"({resultats[meilleur_algo]['nb_creneaux']} créneaux/couleurs)",
        fichier="graphe_colore.png"
    )

    # -----------------------------------------------------------------------
    # PARTIE 3 — Affectation des salles et planning final
    # -----------------------------------------------------------------------
    print("\n" + "━" * 60)
    print("  PARTIE 3 — Affectation des salles et planning")
    print("━" * 60)

    affectation = Affectation(
        salles=SALLES_DISPO,
        ues_info=UES_INFO,
        nb_creneaux_par_jour=4
    )

    print("\n  Affectation des salles en cours...")
    affectation.affecter(coloration_finale, interdictions_jour=INTERDICTIONS_JOUR)

    # Rapport d'audit
    affectation.afficher_rapport_audit(coloration_finale)

    # Planning final
    planning = Planning(affectation)
    planning.afficher_console()
    planning.statistiques()

    # Export CSV
    planning.exporter_csv("planning.csv")

    # -----------------------------------------------------------------------
    # Résumé final
    # -----------------------------------------------------------------------
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║                 FICHIERS GÉNÉRÉS                        ║")
    print("╠" + "═" * 58 + "╣")
    print("║  graphe_non_colore.png  — graphe de conflits brut       ║")
    print("║  graphe_colore.png      — graphe avec créneaux colorés   ║")
    print("║  planning.csv           — planning créneau × salle       ║")
    print("╚" + "═" * 58 + "╝\n")


if __name__ == "__main__":
    main()
