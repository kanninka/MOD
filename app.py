"""
app.py — Application Streamlit pour la planification d'examens par coloration de graphes.
Projet L2 Informatique — Théorie des Graphes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import io
import time
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

from donnees import (
    UES_DEFAUT, INSCRIPTIONS_DEFAUT, SALLES_DEFAUT, CONFIG_PERIODE_DEFAUT,
    calculer_effectifs, etudiants_par_ue,
)
from graphe import GrapheConflits
from coloration import welsh_powell, dsatur, comparer_algorithmes, verifier_coloration
from affectation import affecter_salles, generer_rapport_audit
from planning import generer_planning, exporter_csv, exporter_csv_detail

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Planification d'Examens — Coloration de Graphes",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Initialisation du session_state
# ---------------------------------------------------------------------------

def init_state():
    if "ues" not in st.session_state:
        st.session_state.ues = dict(UES_DEFAUT)
    if "inscriptions_brutes" not in st.session_state:
        st.session_state.inscriptions_brutes = dict(INSCRIPTIONS_DEFAUT)
    if "salles" not in st.session_state:
        st.session_state.salles = dict(SALLES_DEFAUT)
    if "config_periode" not in st.session_state:
        st.session_state.config_periode = dict(CONFIG_PERIODE_DEFAUT)
    if "graphe" not in st.session_state:
        st.session_state.graphe = None
    if "coloration_wp" not in st.session_state:
        st.session_state.coloration_wp = None
    if "coloration_ds" not in st.session_state:
        st.session_state.coloration_ds = None
    if "algo_choisi" not in st.session_state:
        st.session_state.algo_choisi = "Welsh-Powell"
    if "planning_list" not in st.session_state:
        st.session_state.planning_list = None
    if "planning_struct" not in st.session_state:
        st.session_state.planning_struct = None
    if "rapport_audit" not in st.session_state:
        st.session_state.rapport_audit = None

init_state()

# ---------------------------------------------------------------------------
# Palette de couleurs pour les créneaux
# ---------------------------------------------------------------------------

PALETTE = [
    "#E63946", "#457B9D", "#2A9D8F", "#E9C46A", "#F4A261",
    "#264653", "#8338EC", "#06D6A0", "#FB5607", "#3A86FF",
    "#FFBE0B", "#8AC926", "#FF595E", "#6A4C93", "#1982C4",
    "#F72585", "#4CC9F0", "#43AA8B", "#90BE6D", "#F8961E",
]

def couleur_creneau(n: int) -> str:
    return PALETTE[(n - 1) % len(PALETTE)]

# ---------------------------------------------------------------------------
# Sidebar — Navigation & Configuration
# ---------------------------------------------------------------------------

st.sidebar.title("🎓 Planification d'Examens")
st.sidebar.markdown("**Coloration de Graphes — L2 Informatique**")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["📋 Données", "🔗 Graphe de Conflits", "🎨 Coloration", "📅 Planning Final", "✅ Audit"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.subheader("⚙️ Période d'examens")
st.session_state.config_periode["nb_jours"] = st.sidebar.number_input(
    "Nombre de jours", min_value=1, max_value=10,
    value=st.session_state.config_periode["nb_jours"]
)
st.session_state.config_periode["creneaux_par_jour"] = st.sidebar.number_input(
    "Créneaux par jour", min_value=1, max_value=6,
    value=st.session_state.config_periode["creneaux_par_jour"]
)

st.sidebar.divider()
if st.sidebar.button("🔄 Réinitialiser les données", use_container_width=True):
    for k in ["ues", "inscriptions_brutes", "salles", "config_periode",
              "graphe", "coloration_wp", "coloration_ds",
              "planning_list", "planning_struct", "rapport_audit"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def construire_graphe():
    """Construit le graphe à partir des données de session."""
    g = GrapheConflits()
    inscriptions = etudiants_par_ue(st.session_state.inscriptions_brutes)
    g.construire_depuis_inscriptions(st.session_state.ues, inscriptions)
    return g, inscriptions

def effectifs():
    return calculer_effectifs(st.session_state.inscriptions_brutes)

# ---------------------------------------------------------------------------
# PAGE 1 — Données
# ---------------------------------------------------------------------------

if page == "📋 Données":
    st.title("📋 Données de la période d'examens")

    tab_ue, tab_et, tab_salles = st.tabs(["Unités d'Enseignement", "Inscriptions étudiantes", "Salles"])

    # --- Onglet UEs ---
    with tab_ue:
        st.subheader("Unités d'Enseignement (UEs)")
        eff = effectifs()
        rows = []
        for code, info in st.session_state.ues.items():
            rows.append({
                "Code": code,
                "Nom": info["nom"],
                "Enseignant": info["enseignant"],
                "Nb étudiants": eff.get(code, 0),
                "Nécessite labo": "✅" if info.get("necessite_labo") else "❌",
                "Filière": info.get("filiere", ""),
            })
        df_ue = pd.DataFrame(rows)
        st.dataframe(df_ue, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("➕ Ajouter une UE")
        with st.form("form_ajout_ue"):
            c1, c2, c3 = st.columns(3)
            code_new = c1.text_input("Code UE (ex: STAT)").upper().strip()
            nom_new = c2.text_input("Nom de l'UE")
            enseignant_new = c3.text_input("Enseignant")
            c4, c5 = st.columns(2)
            labo_new = c4.checkbox("Nécessite un laboratoire")
            filiere_new = c5.text_input("Filière", value="INFO")
            if st.form_submit_button("Ajouter l'UE"):
                if code_new and nom_new:
                    if code_new in st.session_state.ues:
                        st.error(f"Le code '{code_new}' existe déjà.")
                    else:
                        st.session_state.ues[code_new] = {
                            "nom": nom_new,
                            "enseignant": enseignant_new,
                            "necessite_labo": labo_new,
                            "filiere": filiere_new,
                        }
                        st.session_state.graphe = None
                        st.success(f"UE '{code_new}' ajoutée.")
                        st.rerun()
                else:
                    st.warning("Veuillez renseigner le code et le nom.")

    # --- Onglet Inscriptions ---
    with tab_et:
        st.subheader("Inscriptions étudiantes")
        codes_ues = list(st.session_state.ues.keys())
        rows_et = []
        for etudiant, ues_list in st.session_state.inscriptions_brutes.items():
            rows_et.append({
                "Étudiant": etudiant,
                "UEs inscrites": ", ".join(ues_list),
                "Nombre d'UEs": len(ues_list),
            })
        df_et = pd.DataFrame(rows_et)
        st.dataframe(df_et, use_container_width=True, hide_index=True)
        st.info(f"**{len(st.session_state.inscriptions_brutes)}** étudiants enregistrés.")

        st.divider()
        st.subheader("➕ Ajouter un étudiant")
        with st.form("form_ajout_etudiant"):
            c1, c2 = st.columns([1, 2])
            id_et = c1.text_input("ID Étudiant (ex: E031)").upper().strip()
            ues_choisies = c2.multiselect("UEs inscrites", options=codes_ues)
            if st.form_submit_button("Ajouter"):
                if id_et and ues_choisies:
                    st.session_state.inscriptions_brutes[id_et] = ues_choisies
                    st.session_state.graphe = None
                    st.success(f"Étudiant '{id_et}' ajouté.")
                    st.rerun()
                else:
                    st.warning("ID et au moins une UE requis.")

    # --- Onglet Salles ---
    with tab_salles:
        st.subheader("Salles disponibles")
        rows_s = []
        for code, info in st.session_state.salles.items():
            rows_s.append({
                "Code": code,
                "Nom": info["nom"],
                "Capacité": info["capacite"],
                "Type": "🖥️ Labo" if info["est_labo"] else "🏫 Standard",
            })
        df_s = pd.DataFrame(rows_s)
        st.dataframe(df_s, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("➕ Ajouter une salle")
        with st.form("form_salle"):
            c1, c2, c3 = st.columns(3)
            code_s = c1.text_input("Code salle").upper().strip()
            nom_s = c2.text_input("Nom de la salle")
            cap_s = c3.number_input("Capacité", min_value=1, max_value=500, value=30)
            est_labo_s = st.checkbox("C'est un laboratoire informatique")
            if st.form_submit_button("Ajouter la salle"):
                if code_s and nom_s:
                    st.session_state.salles[code_s] = {
                        "nom": nom_s,
                        "capacite": cap_s,
                        "est_labo": est_labo_s,
                    }
                    st.success(f"Salle '{code_s}' ajoutée.")
                    st.rerun()

# ---------------------------------------------------------------------------
# PAGE 2 — Graphe de Conflits
# ---------------------------------------------------------------------------

elif page == "🔗 Graphe de Conflits":
    st.title("🔗 Graphe de Conflits entre UEs")
    st.markdown(
        "Chaque **sommet** représente une UE. Une **arête** relie deux UEs qui partagent "
        "au moins un étudiant en commun — elles ne peuvent donc pas être simultanées."
    )

    if st.button("🏗️ Construire / Actualiser le graphe", type="primary"):
        with st.spinner("Construction du graphe..."):
            g, inscriptions = construire_graphe()
            st.session_state.graphe = g
            st.session_state.coloration_wp = None
            st.session_state.coloration_ds = None
            st.session_state.planning_list = None
        st.success("Graphe construit avec succès !")

    if st.session_state.graphe is None:
        st.info("Cliquez sur **Construire le graphe** pour démarrer.")
    else:
        g = st.session_state.graphe
        stats = g.statistiques()

        # Métriques
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Sommets (UEs)", stats["nb_sommets"])
        col2.metric("Arêtes (conflits)", stats["nb_aretes"])
        col3.metric("Degré max", stats["degre_max"])
        col4.metric("Degré moyen", f"{stats['degre_moyen']:.1f}")

        st.divider()
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.subheader("Visualisation du graphe")
            fig, ax = plt.subplots(figsize=(9, 7))
            G = nx.Graph()
            for s in g.sommets:
                G.add_node(s)
            for u, v in g.aretes():
                G.add_edge(u, v)

            pos = nx.spring_layout(G, seed=42, k=1.5)
            degres = dict(G.degree())
            tailles = [400 + degres[n] * 120 for n in G.nodes()]

            nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.4, edge_color="#888", width=1.5)
            nx.draw_networkx_nodes(G, pos, ax=ax, node_size=tailles,
                                   node_color="#457B9D", alpha=0.9)
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=9,
                                    font_color="white", font_weight="bold")
            ax.set_title("Graphe de conflits (taille ∝ degré)", fontsize=13, pad=15)
            ax.axis("off")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        with col_right:
            st.subheader("Degrés des sommets")
            df_deg = pd.DataFrame(
                stats["sommets_par_degre"], columns=["UE", "Degré"]
            )
            df_deg["Nom"] = df_deg["UE"].map(
                lambda c: st.session_state.ues.get(c, {}).get("nom", c)
            )
            st.dataframe(df_deg[["UE", "Nom", "Degré"]], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Matrice d'adjacence")
        noms = g.sommets
        mat = g.matrice
        df_mat = pd.DataFrame(mat, index=noms, columns=noms)
        st.dataframe(df_mat.style.applymap(
            lambda v: "background-color:#457B9D; color:white" if v == 1 else ""
        ), use_container_width=True)

        st.divider()
        st.subheader("Liste d'adjacence")
        rows_adj = []
        for ue in g.sommets:
            voisins = g.voisins(ue)
            rows_adj.append({
                "UE": ue,
                "Nom": st.session_state.ues.get(ue, {}).get("nom", ue),
                "Degré": len(voisins),
                "Voisins (UEs en conflit)": ", ".join(sorted(voisins)) if voisins else "Aucun",
            })
        st.dataframe(pd.DataFrame(rows_adj), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# PAGE 3 — Coloration
# ---------------------------------------------------------------------------

elif page == "🎨 Coloration":
    st.title("🎨 Algorithmes de Coloration")

    if st.session_state.graphe is None:
        st.warning("⚠️ Construisez d'abord le graphe (page **Graphe de Conflits**).")
    else:
        g = st.session_state.graphe

        if st.button("▶️ Exécuter les deux algorithmes et comparer", type="primary"):
            with st.spinner("Exécution des algorithmes..."):
                resultats = comparer_algorithmes(g)
            st.session_state.coloration_wp = resultats["Welsh-Powell"]["coloration"]
            st.session_state.coloration_ds = resultats["DSATUR"]["coloration"]
            st.session_state._resultats_algo = resultats
            st.session_state.planning_list = None
            st.session_state.planning_struct = None

        if "coloration_wp" not in st.session_state or st.session_state.coloration_wp is None:
            st.info("Cliquez sur **Exécuter** pour lancer la coloration.")
        else:
            resultats = st.session_state._resultats_algo

            # Résumé de comparaison
            st.subheader("📊 Comparaison des algorithmes")
            meilleur = resultats["meilleur"]
            wp = resultats["Welsh-Powell"]
            ds = resultats["DSATUR"]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Welsh-Powell — Créneaux", wp["nb_creneaux"],
                          delta=None if meilleur == "Égalité" else ("✓ meilleur" if meilleur == "Welsh-Powell" else ""))
                st.metric("Welsh-Powell — Temps", f"{wp['temps_ms']} ms")
            with col2:
                st.metric("DSATUR — Créneaux", ds["nb_creneaux"],
                          delta=None if meilleur == "Égalité" else ("✓ meilleur" if meilleur == "DSATUR" else ""))
                st.metric("DSATUR — Temps", f"{ds['temps_ms']} ms")
            with col3:
                if meilleur == "Égalité":
                    st.info("**Égalité** — les deux algorithmes donnent le même nombre de créneaux.")
                else:
                    st.success(f"**{meilleur}** utilise moins de créneaux.")

            st.divider()

            # Choix de l'algorithme pour le planning
            st.subheader("✅ Choisir l'algorithme pour le planning")
            st.session_state.algo_choisi = st.radio(
                "Algorithme à utiliser :",
                ["Welsh-Powell", "DSATUR"],
                horizontal=True,
            )
            coloration_active = (
                st.session_state.coloration_wp
                if st.session_state.algo_choisi == "Welsh-Powell"
                else st.session_state.coloration_ds
            )

            # Vérification
            valide = verifier_coloration(g, coloration_active)
            if valide:
                st.success("✅ Coloration valide — aucune paire de UEs adjacentes n'a le même créneau.")
            else:
                st.error("❌ Coloration invalide !")

            st.divider()

            # Visualisation du graphe coloré
            st.subheader("🎨 Graphe coloré")
            col_v, col_t = st.columns([3, 2])

            with col_v:
                fig, ax = plt.subplots(figsize=(9, 7))
                G = nx.Graph()
                for s in g.sommets:
                    G.add_node(s)
                for u, v in g.aretes():
                    G.add_edge(u, v)

                pos = nx.spring_layout(G, seed=42, k=1.5)
                node_colors = [couleur_creneau(coloration_active[n]) for n in G.nodes()]

                nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.35, edge_color="#888", width=1.5)
                nx.draw_networkx_nodes(G, pos, ax=ax, node_size=700,
                                       node_color=node_colors, alpha=0.95)
                nx.draw_networkx_labels(G, pos, ax=ax, font_size=9,
                                        font_color="white", font_weight="bold")

                nb_c = max(coloration_active.values())
                legendes = [
                    mpatches.Patch(color=couleur_creneau(c), label=f"Créneau {c}")
                    for c in range(1, nb_c + 1)
                ]
                ax.legend(handles=legendes, loc="upper left", fontsize=8,
                          ncol=2, framealpha=0.8)
                ax.set_title(
                    f"Graphe coloré — {st.session_state.algo_choisi} ({nb_c} créneaux)",
                    fontsize=13, pad=15
                )
                ax.axis("off")
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

                # Bouton télécharger PNG
                buf = io.BytesIO()
                fig2, ax2 = plt.subplots(figsize=(10, 8))
                nx.draw_networkx_edges(G, pos, ax=ax2, alpha=0.35, edge_color="#888", width=1.5)
                nx.draw_networkx_nodes(G, pos, ax=ax2, node_size=700,
                                       node_color=node_colors, alpha=0.95)
                nx.draw_networkx_labels(G, pos, ax=ax2, font_size=9,
                                        font_color="white", font_weight="bold")
                ax2.legend(handles=legendes, loc="upper left", fontsize=8,
                           ncol=2, framealpha=0.8)
                ax2.set_title(
                    f"Graphe coloré — {st.session_state.algo_choisi} ({nb_c} créneaux)",
                    fontsize=13, pad=15
                )
                ax2.axis("off")
                fig2.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                plt.close(fig2)
                buf.seek(0)
                st.download_button(
                    "📥 Télécharger le graphe coloré (PNG)",
                    data=buf,
                    file_name="graphe_colore.png",
                    mime="image/png",
                )

            with col_t:
                st.subheader("Affectation des créneaux")
                rows_col = []
                for ue, creneau in sorted(coloration_active.items(), key=lambda x: x[1]):
                    rows_col.append({
                        "UE": ue,
                        "Nom": st.session_state.ues.get(ue, {}).get("nom", ue),
                        "Créneau": creneau,
                    })
                df_col = pd.DataFrame(rows_col)
                st.dataframe(df_col, use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("Répartition par créneau")
                repartition = resultats[st.session_state.algo_choisi]["repartition"]
                for c in sorted(repartition.keys()):
                    with st.expander(f"Créneau {c} — {len(repartition[c])} UE(s)", expanded=c <= 3):
                        for ue in sorted(repartition[c]):
                            nom = st.session_state.ues.get(ue, {}).get("nom", ue)
                            st.write(f"• **{ue}** — {nom}")

# ---------------------------------------------------------------------------
# PAGE 4 — Planning Final
# ---------------------------------------------------------------------------

elif page == "📅 Planning Final":
    st.title("📅 Planning Final des Examens")

    coloration_active = None
    if st.session_state.coloration_wp is not None:
        coloration_active = (
            st.session_state.coloration_wp
            if st.session_state.algo_choisi == "Welsh-Powell"
            else st.session_state.coloration_ds
        )

    if coloration_active is None:
        st.warning("⚠️ Effectuez d'abord la coloration (page **Coloration**).")
    else:
        eff = effectifs()
        if st.button("📅 Générer le planning et affecter les salles", type="primary"):
            with st.spinner("Affectation des salles et génération du planning..."):
                inscriptions = etudiants_par_ue(st.session_state.inscriptions_brutes)
                planning_list = affecter_salles(
                    coloration=coloration_active,
                    ues=st.session_state.ues,
                    effectifs=eff,
                    salles=st.session_state.salles,
                )
                planning_struct = generer_planning(
                    planning=planning_list,
                    ues=st.session_state.ues,
                    salles=st.session_state.salles,
                    effectifs=eff,
                    nb_jours=st.session_state.config_periode["nb_jours"],
                    creneaux_par_jour=st.session_state.config_periode["creneaux_par_jour"],
                    noms_creneaux=st.session_state.config_periode["noms_creneaux"],
                )
                audit = generer_rapport_audit(
                    planning=planning_list,
                    ues=st.session_state.ues,
                    salles=st.session_state.salles,
                    coloration=coloration_active,
                    graphe=st.session_state.graphe,
                )
                st.session_state.planning_list = planning_list
                st.session_state.planning_struct = planning_struct
                st.session_state.rapport_audit = audit
            st.success("Planning généré !")

        if st.session_state.planning_struct is not None:
            ps = st.session_state.planning_struct

            # Résumé
            col1, col2, col3 = st.columns(3)
            col1.metric("Créneaux utilisés", ps["nb_creneaux_utilises"])
            col2.metric("Créneaux disponibles", ps["nb_creneaux_disponibles"])
            excedent = max(0, ps["nb_creneaux_utilises"] - ps["nb_creneaux_disponibles"])
            col3.metric("Créneaux excédentaires", excedent,
                        delta_color="inverse" if excedent > 0 else "normal")

            if excedent > 0:
                st.warning(
                    f"⚠️ Le nombre de créneaux nécessaires ({ps['nb_creneaux_utilises']}) dépasse "
                    f"la capacité de la période ({ps['nb_creneaux_disponibles']} créneaux). "
                    "Augmentez le nombre de jours ou de créneaux par jour dans la barre latérale."
                )

            st.divider()

            # Tableau planning par jour
            for jour_info in ps["jours"]:
                st.subheader(f"📆 Jour {jour_info['jour']}")
                for slot in jour_info["slots"]:
                    examens = slot["examens"]
                    label = f"🕐 {slot['nom']} — {len(examens)} examen(s)"
                    if examens:
                        with st.expander(label, expanded=True):
                            rows_ex = []
                            for ex in examens:
                                rows_ex.append({
                                    "UE": ex["ue_code"],
                                    "Nom de l'UE": ex["ue_nom"],
                                    "Salle": f"{ex['salle_code']} ({ex['salle_nom']})",
                                    "Nb étudiants": ex["nb_etudiants"],
                                    "Enseignant": ex["enseignant"],
                                    "Labo": "🖥️" if ex["necessite_labo"] else "",
                                    "Statut": "✅" if ex["ok"] else "❌",
                                })
                            st.dataframe(pd.DataFrame(rows_ex), use_container_width=True, hide_index=True)
                    else:
                        st.caption(f"  🕐 {slot['nom']} — Aucun examen")

            # Créneaux surplus
            if ps["surplus"]:
                st.error("❌ Les UEs suivantes n'ont pas pu être placées dans la période définie :")
                st.dataframe(pd.DataFrame(ps["surplus"]), use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("📥 Exports CSV")
            c1, c2 = st.columns(2)
            with c1:
                csv_grille = exporter_csv(ps, st.session_state.salles)
                st.download_button(
                    "📄 Planning (créneau × salle)",
                    data=csv_grille.encode("utf-8-sig"),
                    file_name="planning_creneau_salle.csv",
                    mime="text/csv",
                )
            with c2:
                csv_detail = exporter_csv_detail(
                    st.session_state.planning_list,
                    st.session_state.ues,
                    st.session_state.salles,
                    eff,
                )
                st.download_button(
                    "📄 Planning détaillé (une ligne par UE)",
                    data=csv_detail.encode("utf-8-sig"),
                    file_name="planning_detail.csv",
                    mime="text/csv",
                )

# ---------------------------------------------------------------------------
# PAGE 5 — Audit
# ---------------------------------------------------------------------------

elif page == "✅ Audit":
    st.title("✅ Rapport d'Audit des Contraintes")

    if st.session_state.rapport_audit is None:
        st.warning("⚠️ Générez d'abord le planning (page **Planning Final**).")
    else:
        audit = st.session_state.rapport_audit

        # Score global
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vérifications totales", audit["total_checks"])
        col2.metric("Vérifications réussies", audit["ok_count"])
        col3.metric("Violations", audit["nb_violations"],
                    delta_color="inverse" if audit["nb_violations"] > 0 else "normal")
        col4.metric("Score de conformité", f"{audit['score']} %")

        if audit["valide"]:
            st.success("🎉 **Planning valide** — toutes les contraintes critiques sont respectées !")
        else:
            st.error("❌ **Planning invalide** — des contraintes critiques ne sont pas respectées.")

        st.divider()

        if audit["violations"]:
            st.subheader("🚨 Violations détectées")
            for i, v in enumerate(audit["violations"], 1):
                gravite = v["gravite"]
                if gravite == "CRITIQUE":
                    st.error(f"**[{i}] {v['type']}** — {v['detail']}")
                else:
                    st.warning(f"**[{i}] {v['type']}** — {v['detail']}")
        else:
            st.success("Aucune violation détectée.")

        st.divider()
        st.subheader("📋 Récapitulatif des contraintes")

        contraintes = [
            ("Pas deux UEs en conflit au même créneau", "Obligatoire"),
            ("Une salle = un seul examen par créneau", "Obligatoire"),
            ("Capacité salle ≥ effectif de l'UE", "Obligatoire"),
            ("UE nécessitant un labo → salle labo", "Obligatoire"),
            ("Toutes les UEs ont une salle affectée", "Obligatoire"),
        ]
        df_c = pd.DataFrame(contraintes, columns=["Contrainte", "Type"])
        st.dataframe(df_c, use_container_width=True, hide_index=True)

        # Récap par UE
        st.divider()
        st.subheader("📑 Détail par UE")
        if st.session_state.planning_list:
            rows_ue = []
            for e in sorted(st.session_state.planning_list, key=lambda x: x.creneau):
                rows_ue.append({
                    "UE": e.ue_code,
                    "Nom": st.session_state.ues.get(e.ue_code, {}).get("nom", ""),
                    "Créneau": e.creneau,
                    "Salle": e.salle_code or "—",
                    "Nb étudiants": e.nb_etudiants,
                    "Statut": "✅ OK" if e.ok else f"❌ {e.raison_echec}",
                })
            st.dataframe(pd.DataFrame(rows_ue), use_container_width=True, hide_index=True)
