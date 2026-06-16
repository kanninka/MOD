# donnees.py

# 1. Données par défaut
UES_DEFAUT = {
    "MATH101": {"nom": "Mathématiques", "enseignant": "Dr. Smith", "necessite_labo": False, "filiere": "INFO"},
    "INFO102": {"nom": "Programmation", "enseignant": "Pr. Doe", "necessite_labo": True, "filiere": "INFO"},
    "PHYS103": {"nom": "Physique", "enseignant": "Dr. Brown", "necessite_labo": False, "filiere": "PHYS"},
}

INSCRIPTIONS_DEFAUT = {
    "E01": ["MATH101", "PHYS103"],
    "E02": ["MATH101", "INFO102"],
    "E03": ["MATH101", "INFO102"],
    "E04": ["MATH101", "PHYS103"],
}

SALLES_DEFAUT = {
    "A1001": {"nom": "Amphi A", "capacite": 50, "est_labo": False},
    "A1002":  {"nom": "Labo Info", "capacite": 30, "est_labo": True},
}

CONFIG_PERIODE_DEFAUT = {
    "nb_jours": 3,
    "creneaux_par_jour": 4,
    "noms_creneaux": ["08h-10h", "10h-12h", "14h-16h", "16h-18h"]
}

# 2. Fonctions utilitaires nécessaires à app.py
def calculer_effectifs(inscriptions):
    """Calcule le nombre d'étudiants par UE."""
    effectifs = {}
    for etudiant, ues in inscriptions.items():
        for ue in ues:
            effectifs[ue] = effectifs.get(ue, 0) + 1
    return effectifs

def etudiants_par_ue(inscriptions):
    """Transforme {etudiant: [ues]} en {ue: {etudiants}}."""
    ue_etudiants = {}
    for etudiant, ues in inscriptions.items():
        for ue in ues:
            if ue not in ue_etudiants:
                ue_etudiants[ue] = set()
            ue_etudiants[ue].add(etudiant)
    return ue_etudiants
