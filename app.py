import streamlit as st
import base64

# ⚠️ La première ligne DOIT être set_page_config
st.set_page_config(page_title="FACTORYAWAKENING", page_icon="🏭", layout="wide")

# Imports nécessaires
from login import show_login  
from appf import show_chatbot
from quality import show_dashboard
from maintenance import show_main  # ✅ Module Maintenance ajouté
from optimisation import show_optimisation  # ✅ Module Optimisation ajouté
from alerte import show_alerte  # ✅ Module Alerte ajouté

# Masquer la barre du haut de Streamlit
hide_top_bar = """
    <style>
    header[data-testid="stHeader"] {
        display: none;
    }
    </style>
"""
st.markdown(hide_top_bar, unsafe_allow_html=True)

# Fonction pour définir l'image de fond
def set_background(image_file):
    try:
        with open(image_file, "rb") as file:
            encoded = base64.b64encode(file.read()).decode()
        st.markdown(f"""
            <style>
                .stApp {{
                    background-image: url("data:image/png;base64,{encoded}");
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
                #MainMenu {{visibility: hidden;}}
                footer {{visibility: hidden;}}
                header {{visibility: hidden;}}
                [data-testid="stToolbar"] {{display: none !important;}}
            </style>
        """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Image de fond '{image_file}' non trouvée.")

# Page d'accueil
def page_accueil(image_file="DecGen.png"):
    set_background(image_file)
    
    user_info = st.session_state.get("username", st.session_state.get("user_email", "Utilisateur"))

    # ✅ Bienvenue + bouton Déconnexion côte à côte
    col_left, col_right = st.columns([4, 1])
    with col_left:
        st.markdown(f"### Bienvenue, {user_info}! 👋")
    with col_right:
        if st.button("Se déconnecter", key="logout_btn_top"):
            keys_to_keep = ["authenticated", "page"]
            keys_to_delete = [key for key in st.session_state.keys() if key not in keys_to_keep]
            for key in keys_to_delete:
                del st.session_state[key]
            st.session_state["authenticated"] = False
            st.session_state["page"] = "login"
            st.rerun()

    # ✅ Cinq colonnes horizontalement
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown("""
            <div class="card">
                <img src="https://img.icons8.com/?size=100&id=V9RZq9VhPPDM&format=png&color=000000"/>
                <h4>Phosspectrom AI</h4>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Essayez Phosspectrom AI", key="dashboard_btn"):
            st.session_state["page"] = "dashboard"
            st.rerun()

    with col2:
        st.markdown("""
            <div class="card">
                <img src="https://img.icons8.com/?size=100&id=70098&format=png&color=000000"/>
                <h4>Alertify AI</h4>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Essayez Alertify AI", key="alerte_btn"):
            st.session_state["page"] = "alerte"
            st.rerun()

    with col3:
        st.markdown("""
            <div class="card">
                <img src="https://img.icons8.com/?size=100&id=10758&format=png&color=000000"/>
                <h4>SmartMOP</h4>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Essayez smartmop", key="maintenance_btn"):
            st.session_state["page"] = "maintenance"
            st.rerun()

    with col4:
        st.markdown("""
            <div class="card">
                <img src="https://img.icons8.com/?size=100&id=w0vclwHRccbk&format=png&color=000000"/>
                <h4>ChainMind AI</h4>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Essayez ChainMind AI", key="optimisation_btn"):
            st.session_state["page"] = "optimisation"
            st.rerun()

    with col5:
        st.markdown("""
            <div class="card">
                <img src="https://img.icons8.com/?size=100&id=AQdX4guXSINv&format=png&color=000000"/>
                <h4>FactoryBot</h4>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Essayez FactoryBot", key="factorybot_btn"):
            st.session_state["page"] = "factorybot"
            st.rerun()

    # ✅ CSS pour cartes plus grandes ET PLUS LARGES
    st.markdown("""
        <style>
            .card {
                background-color: rgba(255, 255, 255, 0.85);
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
                margin: 20px;
                transition: transform 0.2s;
                height: 300px;
                width: 100%;
                max-width: 350px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }
            .card:hover {
                transform: scale(1.05);
            }
            .card img {
                width: 90px;
                height: 90px;
                margin-bottom: 20px;
            }
            .card h4 {
                margin: 15px 0;
                font-size: 24px;
                color: #2c3e50;
                font-weight: bold;
            }
            .stButton > button {
                width: 100%;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                background-color: #7cd1d6 !important;
                color: white !important;
                border: none !important;
                transition: background-color 0.3s;
            }
            .stButton > button:hover {
                background-color: #5ab6bc !important;
            }
        </style>
    """, unsafe_allow_html=True)

# Fonction principale
def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "login"
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state.get("authenticated", False):
        show_login()
    else:
        current_page = st.session_state.get("page", "accueil")
        
        if current_page == "accueil":
            page_accueil()
        elif current_page == "factorybot":
            show_chatbot()
        elif current_page == "dashboard":
            show_dashboard()
        elif current_page == "maintenance":
            show_main()
        elif current_page == "optimisation":  # ✅ Nouvelle page Optimisation
            show_optimisation()
        elif current_page == "alerte":  # ✅ Nouvelle page Alerte
            show_alerte()
        else:
            st.session_state["page"] = "accueil"
            st.rerun()

# Exécution
if __name__ == "__main__":
    main()