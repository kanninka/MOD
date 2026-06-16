"""
graphe.py — Construction et représentation du graphe de conflits d'examens.

Un sommet = une UE (Unité d'Enseignement).
Une arête = deux UE partagent au moins un étudiant (conflit).
"""

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class GrapheConflits:
    """
    Représentation d'un graphe de conflits par matrice d'adjacence ET liste d'adjacence.
    """

    def __init__(self, ues: list[str]):
        """
        Initialise le graphe avec la liste des UE.

        :param ues: Liste des identifiants d'UE (ex: ['MATH1', 'INFO2', ...])
        """
        self.ues = list(ues)
        self.n = len(ues)
        self.index = {ue: i for i, ue in enumerate(ues)}  # UE -> indice

        # Matrice d'adjacence (n x n), initialisée à 0
        self.matrice = [[0] * self.n for _ in range(self.n)]

        # Liste d'adjacence : {ue: set(voisins)}
        self.liste = {ue: set() for ue in ues}

    def ajouter_arete(self, ue1: str, ue2: str) -> None:
        """
        Ajoute une arête (conflit) entre ue1 et ue2.

        :param ue1: Identifiant de la première UE
        :param ue2: Identifiant de la deuxième UE
        """
        if ue1 == ue2:
            return
        if ue1 not in self.index or ue2 not in self.index:
            raise ValueError(f"UE inconnue : {ue1} ou {ue2}")

        i, j = self.index[ue1], self.index[ue2]
        self.matrice[i][j] = 1
        self.matrice[j][i] = 1
        self.liste[ue1].add(ue2)
        self.liste[ue2].add(ue1)

    def construire_depuis_inscriptions(self, inscriptions: dict[str, set]) -> None:
        """
        Construit automatiquement le graphe depuis un dictionnaire {ue: {etudiants}}.

        Deux UE sont en conflit si elles partagent au moins un étudiant.

        :param inscriptions: {code_ue: ensemble d'identifiants d'étudiants}
        """
        ues_liste = list(inscriptions.keys())
        for i in range(len(ues_liste)):
            for j in range(i + 1, len(ues_liste)):
                ue1, ue2 = ues_liste[i], ues_liste[j]
                communs = inscriptions[ue1] & inscriptions[ue2]
                if communs:
                    self.ajouter_arete(ue1, ue2)

    def ajouter_contrainte_surveillant(self, ue1: str, ue2: str) -> None:
        """
        Ajoute un conflit entre deux UE qui partagent le même surveillant.
        Identique à ajouter_arete, conservé pour la clarté sémantique.
        """
        self.ajouter_arete(ue1, ue2)

    def ajouter_interdiction_journee(self, ue1: str, ue2: str) -> None:
        """
        Marque deux UE qui ne peuvent pas avoir lieu le même jour
        (contrainte souhaitée — traitée dans affectation.py).
        Stockée séparément, pas comme arête du graphe principal.
        """
        if not hasattr(self, 'interdictions_jour'):
            self.interdictions_jour = set()
        self.interdictions_jour.add((min(ue1, ue2), max(ue1, ue2)))

    def nb_sommets(self) -> int:
        """Retourne le nombre de sommets (UE)."""
        return self.n

    def nb_aretes(self) -> int:
        """Retourne le nombre d'arêtes (conflits)."""
        total = sum(len(voisins) for voisins in self.liste.values())
        return total // 2

    def degre(self, ue: str) -> int:
        """Retourne le degré (nombre de voisins) d'un sommet UE."""
        return len(self.liste[ue])

    def voisins(self, ue: str) -> set:
        """Retourne l'ensemble des voisins d'une UE."""
        return self.liste[ue].copy()

    def afficher_stats(self) -> None:
        """Affiche les statistiques du graphe : sommets, arêtes, degrés."""
        print("=" * 50)
        print("      STATISTIQUES DU GRAPHE DE CONFLITS")
        print("=" * 50)
        print(f"  Nombre de sommets (UE)    : {self.nb_sommets()}")
        print(f"  Nombre d'arêtes (conflits): {self.nb_aretes()}")
        print()
        print("  Degrés des sommets :")
        for ue in self.ues:
            d = self.degre(ue)
            barre = "█" * d
            print(f"    {ue:15s} : {d:2d}  {barre}")
        print("=" * 50)

    def afficher_matrice(self) -> None:
        """Affiche la matrice d'adjacence dans la console."""
        print("\nMatrice d'adjacence :")
        entete = "         " + "  ".join(f"{ue[:4]:4s}" for ue in self.ues)
        print(entete)
        for i, ue in enumerate(self.ues):
            ligne = f"{ue[:8]:8s} " + "  ".join(f"  {self.matrice[i][j]} " for j in range(self.n))
            print(ligne)

    def afficher_liste(self) -> None:
        """Affiche la liste d'adjacence dans la console."""
        print("\nListe d'adjacence :")
        for ue in self.ues:
            voisins_str = ", ".join(sorted(self.liste[ue])) if self.liste[ue] else "∅"
            print(f"  {ue:15s} → {{ {voisins_str} }}")

    def vers_networkx(self) -> nx.Graph:
        """Convertit le graphe en objet networkx pour la visualisation."""
        G = nx.Graph()
        G.add_nodes_from(self.ues)
        for ue in self.ues:
            for voisin in self.liste[ue]:
                if ue < voisin:
                    G.add_edge(ue, voisin)
        return G

    def visualiser(self, coloration: dict[str, int] | None = None,
                   titre: str = "Graphe de Conflits d'Examens",
                   fichier: str | None = "graphe_conflits.png") -> None:
        """
        Visualise le graphe avec networkx et matplotlib.

        :param coloration: {ue: numero_creneau} — si fourni, colorie les noeuds
        :param titre: Titre du graphe affiché
        :param fichier: Chemin de sauvegarde (None = affichage uniquement)
        """
        G = self.vers_networkx()

        # Palette de couleurs pour les créneaux
        palette = [
            "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
            "#1ABC9C", "#E67E22", "#D35400", "#27AE60", "#2980B9",
            "#8E44AD", "#16A085", "#F1C40F", "#C0392B", "#2C3E50",
        ]

        # Attribution des couleurs des noeuds
        if coloration:
            nb_couleurs = max(coloration.values()) + 1
            node_colors = [palette[coloration.get(ue, 0) % len(palette)] for ue in G.nodes()]
        else:
            node_colors = ["#85C1E9"] * len(G.nodes())
            nb_couleurs = 0

        plt.figure(figsize=(14, 10))
        plt.title(titre, fontsize=16, fontweight="bold", pad=20)

        # Disposition : spring layout avec graine fixe pour reproductibilité
        pos = nx.spring_layout(G, seed=42, k=2.5)

        # Dessin du graphe
        nx.draw_networkx_edges(G, pos, alpha=0.4, edge_color="#7F8C8D", width=1.5)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                               node_size=1800, alpha=0.9)
        nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold",
                                font_color="white")

        # Légende des créneaux si coloration fournie
        if coloration and nb_couleurs > 0:
            legendes = [
                mpatches.Patch(color=palette[c % len(palette)], label=f"Créneau {c + 1}")
                for c in range(nb_couleurs)
            ]
            plt.legend(handles=legendes, loc="upper left", fontsize=9,
                       title="Créneaux horaires", title_fontsize=10)

        plt.axis("off")
        plt.tight_layout()

        if fichier:
            plt.savefig(fichier, dpi=150, bbox_inches="tight")
            print(f"  ✓ Graphe sauvegardé : {fichier}")

        plt.show()
        plt.close()
