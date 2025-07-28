# streamlit_app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import os

# CONFIGURATION GÉNÉRALE
st.set_page_config(page_title="Plateforme Maintenance Prédictive", layout="wide")

# TITRE PRINCIPAL
st.title("🔧 Plateforme de Maintenance Prédictive - Chargeuses 994 F1 / F2")
st.markdown("**Visualisation des prédictions RUL et optimisation des ressources**")

# NAVIGATION (sidebar)
page = st.sidebar.radio("Aller à :", [
    "🏠 Home", 
    "📈 Prédictions RUL", 
    "🔎 État des composants",
    "📅 Planification de la maintenance",
    "📝 Rapport journalier"
])

# === PAGE HOME ===
if page == "🏠 Home":
    logo_path = r"C:\Users\hp\Desktop\Code UM6P\SmartMOP.jpeg"  # Remplace par le bon chemin
    
    if os.path.exists(logo_path):
        # Centrage du logo avec des colonnes
        col1, col2, col3 = st.columns([2, 2, 2])
        with col2:
            st.image(logo_path, width=400)
    
    # Titre principal : "Bienvenue sur SmartMOP" en noir + le reste en vert
    st.markdown(
    """
    <h1 style='text-align: center;'>
        <span style="color: #006400;">Bienvenue sur SmartMOP- Smart Maintenance OCP Platform</span>
    </h1>
    """,
    unsafe_allow_html=True
    )

    
    # Texte professionnel
    st.markdown("""
    <div style='text-align: justify; font-size: 16px; line-height: 1.6;'>
    <p><strong>SmartMOP</strong> est une plateforme intelligente développée dans le cadre d’un partenariat stratégique entre <strong>OCP Group</strong> et l’Université <strong>Mohammed VI Polytechnique (UM6P)</strong>.</p>

    <p>Elle vise à accompagner le Groupe OCP dans sa transition vers une <strong>maintenance prédictive optimisée</strong>, en intégrant des approches avancées d'<em>intelligence artificielle</em> et d'<em>optimisation opérationnelle</em>.</p>

    <p><strong>Objectifs clés de SmartMOP :</strong></p>
    <ul>
        <li>Optimiser les stratégies de maintenance prédictive des équipements industriels critiques</li>
        <li>Prédire avec précision le <strong>Remaining Useful Life (RUL)</strong> des composants</li>
        <li>Améliorer la disponibilité et la fiabilité des actifs</li>
        <li>Réduire les coûts de maintenance et les temps d’arrêt non planifiés</li>
        <li>Anticiper les défaillances et soutenir la prise de décision proactive</li>
    </ul>

    <p>La plateforme offre différentes fonctionnalités :</p>
    <ul>
        <li>Visualisation des <strong>prédictions de RUL</strong> par capteur</li>
        <li>Suivi de l’<strong>état de santé des composants</strong></li>
        <li>Optimisation et planification des interventions de maintenance</li>
        <li>Exportation des rapports pour un suivi avancé</li>
    </ul>

    <hr>

    <p style='text-align: center;'><em>Version prototype — développement en cours sous le pilotage de <strong>UM6P</strong> et en collaboration étroite avec les équipes <strong>OCP</strong>.</em></p>
    </div>
    """, unsafe_allow_html=True)




# === PAGE 2 - PRÉDICTIONS RUL ===
elif page == "📈 Prédictions RUL":
    st.header("📈 Prédictions RUL par Capteur")

    # Liste des capteurs
    capteurs = [
        "Température échappement droit",
        "Température échappement gauche",
        "Température liquide refroidissement",
        "Température sortie convertisseur",
        "Température essieux avant",
        "Régime moteur",
        "Température huile direction",
        "Température huile freinage",
        "Température PTO avant",
        "Pression huile moteur"
    ]

    # Choix du capteur
    capteur_choisi = st.selectbox("📌 Choisir un capteur :", capteurs)

    # Dossier où sont stockées les images
    dossier_images = "figures_rul_capteurs"

    # Vérifier que le dossier existe
    if not os.path.exists(dossier_images):
        st.error(f"🚫 Le dossier '{dossier_images}' n'existe pas. Veuillez le créer et y placer vos images.")
    else:
        # Nettoyage du nom pour correspondre au nom des fichiers
        nom_fichier_base = capteur_choisi.replace(" ", "_").replace("é", "e").replace("à", "a").replace("è", "e").replace("/", "_")

        # Fichier attendu
        fichier_pred_vs_real = f"{dossier_images}/{nom_fichier_base}_RUL1.PNG"
        
        # Affichage
        st.markdown(f"### 📊 Capteur sélectionné : **{capteur_choisi}**")

        # Prédictions vs Réalité
        if os.path.exists(fichier_pred_vs_real):
            st.image(fichier_pred_vs_real)
        else:
            st.warning(f"🚫 Image non trouvée : {fichier_pred_vs_real}")

    st.markdown("---")

# === PAGE 5 - ÉTAT DES COMPOSANTS ===
elif page == "🔎 État des composants":
    st.header("🔎 État des composants")

    import random

    # CSS pour largeur + police + lisibilité
    st.markdown(
        """
        <style>
        /* Largeur de la page */
        .main .block-container {
            max-width: 1300px;
            padding-top: 1rem;
            padding-right: 2rem;
            padding-left: 2rem;
            padding-bottom: 2rem;
        }

        /* Agrandir police tableau */
        .css-1v0mbdj, .stDataFrame table {
            font-size: 18px !important;
            line-height: 1.6 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Liste des capteurs
    capteurs = [
        "Température échappement droit",
        "Température échappement gauche",
        "Température liquide refroidissement",
        "Température sortie convertisseur",
        "Température essieux avant",
        "Régime moteur",
        "Température huile direction",
        "Température huile freinage",
        "Température PTO avant",
        "Pression huile moteur"
    ]

    # Jours de la semaine
    jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    # États possibles
    etats_possibles = ["🟢 Bon", "🟡 À surveiller", "🔴 Critique"]

    # Générer un état pour chaque capteur et chaque jour
    data = []
    for jour in jours_semaine:
        for capteur in capteurs:
            etat = random.choice(etats_possibles)
            anomalie = random.choice(["Aucun", "Pression élevée", "Surchauffe", "Temp élevée", "Vibration"])
            action = random.choice(["Surveillance", "Inspection", "Remplacement prévu", "Contrôle régulier"])
            data.append({
                "Jour": jour,
                "Capteur": capteur,
                "État": etat,
                "Dernière anomalie": anomalie,
                "Action recommandée": action
            })

    # Créer le DataFrame
    etat_df = pd.DataFrame(data)

    # Afficher le DataFrame avec plus de hauteur
    st.dataframe(etat_df, height=800)


# === PAGE 6 - PLANIFICATION DE LA MAINTENANCE (IMPORT RESULTATS) ===
elif page == "📅 Planification de la maintenance":
    st.header("📅 Résultats optimisés - Modèle Stochastique (Import des résultats)")

    import os

    # === Chemins vers les images ===
    # ⚠️ Mets ici le bon chemin où tu as sauvegardé tes images
    path_cout = r"C:\Users\hp\Desktop\Code UM6P\newplot.png"
    path_gantt = r"C:\Users\hp\Desktop\Code UM6P\newplot1.png"
    path_achat = r"C:\Users\hp\Desktop\Code UM6P\newplot2.png"

    # === Affichage des résultats ===

    # Coût par scénario
    st.subheader("📊 Comparaison des coûts totaux par scénario (Modèle stochastique)")
    if os.path.exists(path_cout):
        st.image(path_cout, use_column_width=True)
    else:
        st.warning(f"Image non trouvée : {path_cout}")

    # Gantt planification
    st.subheader("📈 Planification optimisée des maintenances (Modèle stochastique)")
    if os.path.exists(path_gantt):
        st.image(path_gantt, use_column_width=True)
    else:
        st.warning(f"Image non trouvée : {path_gantt}")

    # Achats supplémentaires
    st.subheader("📦 Analyse des achats supplémentaires de pièces")
    if os.path.exists(path_achat):
        st.image(path_achat, use_column_width=True)
    else:
        st.warning(f"Image non trouvée : {path_achat}")

# === PAGE 7 - RAPPORT JOURNALIER ===
elif page == "📝 Rapport journalier":
    st.header("📝 Rapport journalier - Synthèse SmartMOP")

    import datetime
    import io
    from fpdf import FPDF
    import os

    # --- 1️⃣ Paramètres du jour ---
    date_rapport = st.date_input("📅 Date du rapport :", datetime.date.today())

    # --- 2️⃣ Etat de santé des composants ---
    st.subheader("🔍 État de santé des composants")

    # Exemple : à remplacer par ton DataFrame réel !
    composants_etat = pd.DataFrame({
        "Composant": [
            "Moteur principal", "Pompe hydraulique", "Transmission", "Circuit de refroidissement",
            "Lubrification moteur", "PTO avant", "Circuit de freinage", "Direction hydraulique",
            "Régime moteur", "Essieux avant"
        ],
        "État": [
            "Bon", "À surveiller", "Critique", "Bon", "Bon", "À surveiller", "Critique", "Bon", "Bon", "Critique"
        ],
        "Dernière anomalie": [
            "Aucun", "Pression élevée", "Surchauffe", "Aucun", "Aucun", "Temp élevée", "Surchauffe", "Aucun", "Aucun", "Vibration"
        ],
        "Action recommandée": [
            "Surveillance", "Inspection", "Remplacement", "Contrôle régulier", "Surveillance",
            "Inspection", "Remplacement", "Surveillance", "Surveillance", "Remplacement"
        ]
    })

    st.dataframe(composants_etat, height=400)

    # --- 3️⃣ Minimisation des coûts ---
    st.subheader("💰 Synthèse de la minimisation des coûts")

    # Exemple : à remplacer par ton vrai df_cout !
    df_cout_exemple = pd.DataFrame({
        'Scénario': ['omega1', 'omega2', 'omega3'],
        'Coût_total (DH)': [74005, 73655, 74305]
    })

    st.dataframe(df_cout_exemple, height=200)

    cout_moyen = df_cout_exemple['Coût_total (DH)'].mean()
    st.info(f"💰 Coût total moyen optimisé : {cout_moyen:,.2f} DH")

    # --- 4️⃣ Consignes pour interventions ---
    st.subheader("🛠️ Consignes pour les interventions du jour")

    # Exemple simple : à remplacer par tes vraies consignes !
    consignes = pd.DataFrame({
        "Composant": ["Transmission", "Circuit de freinage", "Essieux avant"],
        "Technicien assigné": ["Technicien A", "Technicien B", "Technicien C"],
        "Intervention": ["Remplacement", "Contrôle", "Révision"],
        "Début (jour)": [5, 6, 7],
        "Fin (jour)": [7, 8, 9]
    })

    st.dataframe(consignes, height=300)


   