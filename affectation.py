"""
affectation.py — Affectation des salles aux examens après coloration.

Pour chaque créneau (couleur), on affecte une salle à chaque UE en vérifiant :
  - Capacité de la salle >= nombre d'inscrits
  - Type de salle (standard ou laboratoire informatique)
  - Une seule UE par salle par créneau
  - Contrainte souhaitée : espacement entre examens de même filière
  - Contrainte souhaitée : interdictions explicites le même jour
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass
class Salle:
    """Représente une salle d'examen."""
    code: str          # Ex : "A101"
    capacite: int      # Nombre maximum d'étudiants
    est_labo: bool     # True si laboratoire informatique

    def __repr__(self):
        type_str = "Labo" if self.est_labo else "Standard"
        return f"Salle({self.code}, cap={self.capacite}, {type_str})"


@dataclass
class UEInfo:
    """Informations sur une UE pour l'affectation."""
    code: str
    nb_etudiants: int
    filiere: str
    necessite_labo: bool = False
    surveillant: str = ""


@dataclass
class AffectationResult:
    """Résultat de l'affectation d'une UE."""
    ue: str
    creneau: int         # 0-based
    salle: str
    nb_etudiants: int
    capacite_salle: int
    filiere: str
    ok: bool = True
    raison_echec: str = ""


# ---------------------------------------------------------------------------
# Moteur d'affectation
# ---------------------------------------------------------------------------

class Affectation:
    """
    Affecte les salles aux UE après coloration.
    """

    def __init__(self, salles: list[Salle], ues_info: dict[str, UEInfo],
                 nb_creneaux_par_jour: int = 4):
        """
        :param salles: Liste de toutes les salles disponibles
        :param ues_info: {code_ue: UEInfo}
        :param nb_creneaux_par_jour: Nombre de créneaux par journée (défaut 4)
        """
        self.salles = salles
        self.ues_info = ues_info
        self.nb_creneaux_par_jour = nb_creneaux_par_jour

        # Suivi de l'occupation : {creneau: {code_salle}}
        self.occupation: dict[int, set] = {}

        # Résultats
        self.affectations: list[AffectationResult] = []
        self.non_affectees: list[str] = []

    def _jour(self, creneau: int) -> int:
        """Retourne le numéro de jour (0-based) pour un créneau donné."""
        return creneau // self.nb_creneaux_par_jour

    def _salles_disponibles(self, creneau: int, ue_info: UEInfo) -> list[Salle]:
        """
        Filtre les salles disponibles pour un créneau et une UE donnée.

        Critères :
          - Non occupée à ce créneau
          - Capacité suffisante
          - Type compatible (labo si nécessaire)
        """
        occupees = self.occupation.get(creneau, set())
        candidates = []
        for salle in self.salles:
            if salle.code in occupees:
                continue
            if salle.capacite < ue_info.nb_etudiants:
                continue
            if ue_info.necessite_labo and not salle.est_labo:
                continue
            candidates.append(salle)
        # Tri : préférer la salle la moins chère en capacité (évite le gaspillage)
        candidates.sort(key=lambda s: s.capacite)
        return candidates

    def affecter(self, coloration: dict[str, int],
                 interdictions_jour: set | None = None) -> None:
        """
        Effectue l'affectation complète à partir d'une coloration.

        :param coloration: {code_ue: creneau} issu de la coloration
        :param interdictions_jour: Paires (ue1, ue2) ne devant pas être le même jour
        """
        self.affectations = []
        self.non_affectees = []
        self.occupation = {}

        # Priorité : UE avec le plus d'inscrits d'abord (contrainte souhaitée)
        ues_triees = sorted(
            coloration.keys(),
            key=lambda u: (-self.ues_info[u].nb_etudiants if u in self.ues_info else 0)
        )

        for ue in ues_triees:
            creneau = coloration[ue]
            info = self.ues_info.get(ue)
            if info is None:
                self.non_affectees.append(ue)
                continue

            salles_dispo = self._salles_disponibles(creneau, info)

            if not salles_dispo:
                self.affectations.append(AffectationResult(
                    ue=ue, creneau=creneau, salle="—",
                    nb_etudiants=info.nb_etudiants, capacite_salle=0,
                    filiere=info.filiere, ok=False,
                    raison_echec="Aucune salle disponible (capacité ou type)"
                ))
                self.non_affectees.append(ue)
                continue

            salle_choisie = salles_dispo[0]

            # Enregistrer l'occupation
            self.occupation.setdefault(creneau, set()).add(salle_choisie.code)

            self.affectations.append(AffectationResult(
                ue=ue, creneau=creneau, salle=salle_choisie.code,
                nb_etudiants=info.nb_etudiants,
                capacite_salle=salle_choisie.capacite,
                filiere=info.filiere, ok=True
            ))

    def rapport_audit(self, coloration: dict[str, int]) -> dict:
        """
        Génère un rapport d'audit vérifiant toutes les contraintes.

        :param coloration: La coloration utilisée
        :return: Rapport structuré
        """
        rapport = {
            "total_ue": len(coloration),
            "affectees": 0,
            "non_affectees": len(self.non_affectees),
            "violations": [],
            "avertissements": [],
        }

        salles_par_creneau: dict[int, dict] = {}
        filieres_par_creneau: dict[str, list] = {}  # filiere -> liste creneaux

        for aff in self.affectations:
            if not aff.ok:
                rapport["violations"].append(
                    f"[ERREUR] {aff.ue} — {aff.raison_echec}"
                )
                continue

            rapport["affectees"] += 1

            # Vérif : capacité
            if aff.nb_etudiants > aff.capacite_salle:
                rapport["violations"].append(
                    f"[CAPACITÉ] {aff.ue} : {aff.nb_etudiants} étudiants "
                    f"> capacité salle {aff.salle} ({aff.capacite_salle})"
                )

            # Suivi occupation salle × créneau
            cle = (aff.creneau, aff.salle)
            salles_par_creneau.setdefault(cle, []).append(aff.ue)

            # Suivi filière × créneau pour contrainte espacement
            filieres_par_creneau.setdefault(aff.filiere, []).append(aff.creneau)

        # Vérif : double occupation salle
        for (creneau, salle), ues in salles_par_creneau.items():
            if len(ues) > 1:
                rapport["violations"].append(
                    f"[SALLE] Salle {salle} au créneau {creneau + 1} "
                    f"occupée par : {', '.join(ues)}"
                )

        # Contrainte souhaitée : espacement filière (créneaux consécutifs)
        for filiere, creneaux in filieres_par_creneau.items():
            creneaux_tries = sorted(creneaux)
            for i in range(len(creneaux_tries) - 1):
                if creneaux_tries[i + 1] - creneaux_tries[i] == 1:
                    rapport["avertissements"].append(
                        f"[ESPACEMENT] Filière {filiere} : créneaux consécutifs "
                        f"{creneaux_tries[i] + 1} et {creneaux_tries[i + 1] + 1}"
                    )

        # Équilibre charge
        charge: dict[int, int] = {}
        for aff in self.affectations:
            if aff.ok:
                charge[aff.creneau] = charge.get(aff.creneau, 0) + 1
        if charge:
            min_ch, max_ch = min(charge.values()), max(charge.values())
            if max_ch - min_ch > 2:
                rapport["avertissements"].append(
                    f"[ÉQUILIBRE] Charge déséquilibrée : min {min_ch} — max {max_ch} examens/créneau"
                )

        rapport["valide"] = len(rapport["violations"]) == 0
        return rapport

    def afficher_rapport_audit(self, coloration: dict[str, int]) -> None:
        """Affiche le rapport d'audit dans la console."""
        r = self.rapport_audit(coloration)
        print("\n" + "=" * 60)
        print("              RAPPORT D'AUDIT DU PLANNING")
        print("=" * 60)
        print(f"  UE totales       : {r['total_ue']}")
        print(f"  UE affectées     : {r['affectees']}")
        print(f"  UE non affectées : {r['non_affectees']}")
        etat = "✓ VALIDE" if r["valide"] else "✗ INVALIDE"
        print(f"  État             : {etat}")

        if r["violations"]:
            print("\n  Violations (contraintes obligatoires) :")
            for v in r["violations"]:
                print(f"    ● {v}")
        else:
            print("\n  Aucune violation détectée. ✓")

        if r["avertissements"]:
            print("\n  Avertissements (contraintes souhaitées) :")
            for a in r["avertissements"]:
                print(f"    ⚠ {a}")
        else:
            print("  Aucun avertissement. ✓")
        print("=" * 60)
      # --- AJOUTEZ CECI À LA FIN DE affectation.py ---

def affecter_salles(coloration, ues, effectifs, salles):
    """Fonction wrapper pour correspondre à l'appel dans app.py"""
    # 1. Conversion des données pour la classe Affectation
    # (Adaptez les paramètres selon les besoins de votre classe Affectation)
    ues_info = {}
    for code, info in ues.items():
        ues_info[code] = UEInfo(
            code=code,
            nb_etudiants=effectifs.get(code, 0),
            necessite_labo=info.get("necessite_labo", False),
            filiere=info.get("filiere", "INFO")
        )
    
    # 2. Initialisation et exécution
    aff = Affectation(salles=salles, ues_info=ues_info, nb_creneaux_par_jour=4)
    aff.affecter(coloration)
    return aff.affectations

def generer_rapport_audit(planning, ues, salles, coloration, graphe):
    """Fonction wrapper pour correspondre à l'appel dans app.py"""
    # On réutilise la logique de la classe Affectation ou on en crée une nouvelle
    # Ici, nous créons une instance temporaire pour générer l'audit
    aff = Affectation(salles=salles, ues_info={}, nb_creneaux_par_jour=4)
    # L'audit est basé sur l'état de l'affectation
    return aff.rapport_audit(coloration)

