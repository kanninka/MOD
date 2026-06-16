"""
planning.py — Génération du planning final et export CSV.

Produit un tableau créneau × salle avec le code UE et l'effectif,
puis l'exporte en fichier CSV.
"""

import csv
import os
from affectation import Affectation, AffectationResult


# ---------------------------------------------------------------------------
# Génération du planning
# ---------------------------------------------------------------------------

class Planning:
    """
    Construit et exporte le planning final sous forme de tableau créneau × salle.
    """

    JOURS_SEMAINE = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi",
                     "Samedi", "Dimanche"]
    HORAIRES = ["08h00–10h00", "10h15–12h15", "13h30–15h30", "15h45–17h45"]

    def __init__(self, affectation: Affectation):
        """
        :param affectation: L'objet Affectation après exécution de affecter()
        """
        self.affectation = affectation
        self._tableau: dict = {}  # (creneau, salle) -> AffectationResult
        self._construire()

    def _construire(self) -> None:
        """Construit le tableau interne créneau × salle."""
        for aff in self.affectation.affectations:
            if aff.ok:
                self._tableau[(aff.creneau, aff.salle)] = aff

    def _label_creneau(self, creneau: int) -> str:
        """
        Retourne un libellé lisible pour un numéro de créneau.
        Ex : créneau 5 → "Mardi 10h15–12h15"
        """
        nb_par_jour = self.affectation.nb_creneaux_par_jour
        jour_idx = creneau // nb_par_jour
        slot_idx = creneau % nb_par_jour
        jour = self.JOURS_SEMAINE[jour_idx % len(self.JOURS_SEMAINE)]
        horaire = self.HORAIRES[slot_idx % len(self.HORAIRES)]
        return f"{jour} {horaire}"

    def creneaux_utilises(self) -> list[int]:
        """Retourne la liste triée des créneaux effectivement utilisés."""
        return sorted({aff.creneau for aff in self.affectation.affectations if aff.ok})

    def salles_utilisees(self) -> list[str]:
        """Retourne la liste triée des codes de salles effectivement utilisées."""
        return sorted({aff.salle for aff in self.affectation.affectations if aff.ok})

    def afficher_console(self) -> None:
        """Affiche le planning sous forme de tableau texte dans la console."""
        creneaux = self.creneaux_utilises()
        salles = self.salles_utilisees()

        if not creneaux or not salles:
            print("  (Aucun planning à afficher)")
            return

        # Largeur des colonnes
        w_creneau = max(len(self._label_creneau(c)) for c in creneaux) + 2
        w_salle = 20

        print("\n" + "=" * (w_creneau + len(salles) * (w_salle + 1) + 5))
        print("                    PLANNING DES EXAMENS")
        print("=" * (w_creneau + len(salles) * (w_salle + 1) + 5))

        # En-tête (salles)
        entete = f"  {'CRÉNEAU':<{w_creneau}}"
        for s in salles:
            entete += f"| {s:^{w_salle - 1}}"
        print(entete)
        print("  " + "-" * (w_creneau + len(salles) * (w_salle + 1) + 1))

        # Lignes (un créneau par ligne)
        for c in creneaux:
            label = self._label_creneau(c)
            ligne = f"  {label:<{w_creneau}}"
            for s in salles:
                aff = self._tableau.get((c, s))
                if aff:
                    cell = f"{aff.ue} ({aff.nb_etudiants})"
                    ligne += f"| {cell:^{w_salle - 1}}"
                else:
                    ligne += f"| {'—':^{w_salle - 1}}"
            print(ligne)

        print("=" * (w_creneau + len(salles) * (w_salle + 1) + 5))

        # Légende
        print("\n  Légende : UE (nb étudiants)")

        # UE sans salle affectée
        echecs = [aff for aff in self.affectation.affectations if not aff.ok]
        if echecs:
            print(f"\n  ⚠ UE non affectées ({len(echecs)}) :")
            for aff in echecs:
                print(f"    - {aff.ue} : {aff.raison_echec}")

    def exporter_csv(self, chemin: str = "planning.csv") -> None:
        """
        Exporte le planning en fichier CSV au format créneau × salle.

        Format des cellules : "CODE_UE | N étudiants"
        Cellule vide si aucun examen dans ce créneau/salle.

        :param chemin: Chemin du fichier CSV à créer
        """
        creneaux = self.creneaux_utilises()
        salles = self.salles_utilisees()

        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")

            # En-tête
            writer.writerow(["Créneau \\ Salle"] + salles)

            # Lignes
            for c in creneaux:
                label = self._label_creneau(c)
                row = [label]
                for s in salles:
                    aff = self._tableau.get((c, s))
                    if aff:
                        row.append(f"{aff.ue} | {aff.nb_etudiants} étudiants")
                    else:
                        row.append("")
                writer.writerow(row)

            # Feuille récapitulative UE non affectées
            echecs = [aff for aff in self.affectation.affectations if not aff.ok]
            if echecs:
                writer.writerow([])
                writer.writerow(["UE non affectées", "Raison"])
                for aff in echecs:
                    writer.writerow([aff.ue, aff.raison_echec])

        print(f"\n  ✓ Planning exporté : {os.path.abspath(chemin)}")

    def statistiques(self) -> None:
        """Affiche des statistiques résumées du planning."""
        creneaux = self.creneaux_utilises()
        total_examens = len([a for a in self.affectation.affectations if a.ok])
        total_etudiants = sum(a.nb_etudiants for a in self.affectation.affectations if a.ok)

        print("\n" + "=" * 50)
        print("         STATISTIQUES DU PLANNING")
        print("=" * 50)
        print(f"  Nombre de créneaux utilisés : {len(creneaux)}")
        print(f"  Nombre d'examens planifiés  : {total_examens}")
        print(f"  Total d'étudiants convoqués : {total_etudiants}")

        # Charge par créneau
        print("\n  Charge par créneau :")
        for c in creneaux:
            examens_c = [a for a in self.affectation.affectations if a.ok and a.creneau == c]
            label = self._label_creneau(c)
            barre = "█" * len(examens_c)
            print(f"    {label:30s} : {len(examens_c):2d}  {barre}")
        print("=" * 50)
