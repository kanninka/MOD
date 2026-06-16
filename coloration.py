"""
coloration.py — Algorithmes de coloration de graphe.

Implémente :
  - Welsh-Powell : tri par degré décroissant, attribution gloutonne
  - DSATUR      : saturation dynamique, choix du sommet le plus contraint

La "couleur" représente ici un numéro de créneau horaire (0-based).
"""

import time
from graphe import GrapheConflits


# ---------------------------------------------------------------------------
# Utilitaires communs
# ---------------------------------------------------------------------------

def _couleur_min_disponible(ue: str, graphe: GrapheConflits,
                             coloration: dict[str, int]) -> int:
    """
    Retourne le plus petit numéro de créneau non utilisé par les voisins de `ue`.

    :param ue: Identifiant de l'UE à colorer
    :param graphe: Le graphe de conflits
    :param coloration: Coloration partielle actuelle {ue: creneau}
    :return: Indice du premier créneau disponible
    """
    couleurs_voisins = {coloration[v] for v in graphe.voisins(ue) if v in coloration}
    c = 0
    while c in couleurs_voisins:
        c += 1
    return c


def verifier_coloration(graphe: GrapheConflits, coloration: dict[str, int]) -> bool:
    """
    Vérifie qu'aucune arête ne relie deux sommets de même couleur.

    :param graphe: Le graphe de conflits
    :param coloration: {ue: creneau}
    :return: True si la coloration est valide
    """
    for ue in graphe.ues:
        for voisin in graphe.voisins(ue):
            if ue < voisin:  # Chaque arête une seule fois
                if coloration.get(ue) == coloration.get(voisin):
                    return False
    return True


# ---------------------------------------------------------------------------
# Algorithme 1 : Welsh-Powell
# ---------------------------------------------------------------------------

def welsh_powell(graphe: GrapheConflits) -> dict[str, int]:
    """
    Algorithme Welsh-Powell de coloration gloutonne.

    Étapes :
      1. Trier les sommets par degré décroissant.
      2. Parcourir la liste triée ; attribuer à chaque sommet non coloré
         la plus petite couleur non utilisée par ses voisins.

    Complexité : O(n² + m) dans le pire cas.

    :param graphe: Graphe de conflits
    :return: Dictionnaire {ue: numero_creneau}
    """
    # 1. Tri par degré décroissant (à égalité : ordre lexicographique pour reproductibilité)
    ues_triees = sorted(graphe.ues,
                        key=lambda u: (-graphe.degre(u), u))

    coloration: dict[str, int] = {}

    for ue in ues_triees:
        coloration[ue] = _couleur_min_disponible(ue, graphe, coloration)

    return coloration


# ---------------------------------------------------------------------------
# Algorithme 2 : DSATUR
# ---------------------------------------------------------------------------

def dsatur(graphe: GrapheConflits) -> dict[str, int]:
    """
    Algorithme DSATUR (Degree of SATURation).

    À chaque étape, on choisit le sommet non coloré ayant :
      - La plus grande saturation (nombre de couleurs DISTINCTES parmi ses voisins colorés).
      - En cas d'égalité : le degré le plus élevé.
      - En cas d'égalité encore : ordre lexicographique (reproductibilité).

    Complexité : O(n² + m).

    :param graphe: Graphe de conflits
    :return: Dictionnaire {ue: numero_creneau}
    """
    coloration: dict[str, int] = {}

    # saturation[ue] = ensemble des couleurs distinctes parmi ses voisins colorés
    saturation: dict[str, set] = {ue: set() for ue in graphe.ues}

    non_colories = set(graphe.ues)

    while non_colories:
        # Sélection du sommet le plus saturé
        ue_choisi = max(
            non_colories,
            key=lambda u: (len(saturation[u]), graphe.degre(u), [-ord(c) for c in u])
        )

        # Attribution de la couleur minimale disponible
        couleur = _couleur_min_disponible(ue_choisi, graphe, coloration)
        coloration[ue_choisi] = couleur
        non_colories.remove(ue_choisi)

        # Mise à jour de la saturation des voisins non colorés
        for voisin in graphe.voisins(ue_choisi):
            if voisin in non_colories:
                saturation[voisin].add(couleur)

    return coloration


# ---------------------------------------------------------------------------
# Comparaison des deux algorithmes
# ---------------------------------------------------------------------------

def comparer_algorithmes(graphe: GrapheConflits,
                          nb_repetitions: int = 10) -> dict:
    """
    Compare Welsh-Powell et DSATUR sur le graphe donné.

    Mesure :
      - Nombre de créneaux (couleurs) utilisés
      - Temps d'exécution moyen (sur plusieurs répétitions)

    :param graphe: Le graphe à colorer
    :param nb_repetitions: Nombre de fois où chaque algo est lancé pour la mesure de temps
    :return: Dictionnaire de résultats
    """
    resultats = {}

    for nom, algo in [("Welsh-Powell", welsh_powell), ("DSATUR", dsatur)]:
        # Temps d'exécution moyen
        debut = time.perf_counter()
        coloration = None
        for _ in range(nb_repetitions):
            coloration = algo(graphe)
        fin = time.perf_counter()

        temps_moyen_ms = (fin - debut) / nb_repetitions * 1000
        nb_couleurs = max(coloration.values()) + 1
        valide = verifier_coloration(graphe, coloration)

        resultats[nom] = {
            "coloration": coloration,
            "nb_creneaux": nb_couleurs,
            "temps_ms": round(temps_moyen_ms, 4),
            "valide": valide,
        }

    return resultats


def afficher_rapport_coloration(resultats: dict) -> None:
    """
    Affiche un tableau comparatif des deux algorithmes.

    :param resultats: Sortie de comparer_algorithmes()
    """
    print("\n" + "=" * 60)
    print("       COMPARAISON DES ALGORITHMES DE COLORATION")
    print("=" * 60)
    print(f"  {'Algorithme':<20} {'Créneaux':>10} {'Temps (ms)':>12} {'Valide':>8}")
    print("  " + "-" * 54)
    for nom, res in resultats.items():
        valide_str = "✓ Oui" if res["valide"] else "✗ Non"
        print(f"  {nom:<20} {res['nb_creneaux']:>10} {res['temps_ms']:>12.4f} {valide_str:>8}")
    print("=" * 60)

    # Détail des colorations
    for nom, res in resultats.items():
        print(f"\n  Coloration — {nom} ({res['nb_creneaux']} créneau(x)) :")
        # Grouper par créneau
        par_creneau: dict[int, list] = {}
        for ue, c in sorted(res["coloration"].items()):
            par_creneau.setdefault(c, []).append(ue)
        for c in sorted(par_creneau):
            ues = ", ".join(sorted(par_creneau[c]))
            print(f"    Créneau {c + 1:2d} : {ues}")
