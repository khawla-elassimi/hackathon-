import streamlit as st
import base64
from auth import (
    is_valid_email,
    send_verification_code,
    verify_code,
    register_user,
    authenticate_user,
    reset_password,
    is_email_taken,
)

hide_top_bar = """
    <style>
    /* Masquer toute la barre du haut */
    header[data-testid="stHeader"] {
        display: none;
    }
    </style>
"""
st.markdown(hide_top_bar, unsafe_allow_html=True)

def get_base64_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def set_background(image_path):
    img_base64 = get_base64_image(image_path)
    st.markdown(f"""
        <style>
        [data-testid="stApp"] {{
            background-image: url("data:image/jpg;base64,{img_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            height: 100vh;
        }}
        .stButton>button {{
            width: 100%;
        }}
        .link {{
            color: #1f77b4;
            text-decoration: underline;
            cursor: pointer;
        }}
        </style>
    """, unsafe_allow_html=True)

def show_login():
    # Appliquer le fond d'écran (mets le chemin de ton image ici)
    set_background("DecGen.png")

    page = st.session_state.get("page", "login")

    if page == "login":
        st.markdown("<h1 style='text-align: center;'>🔐Connexion</h1>", unsafe_allow_html=True)

        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        if st.button("Se connecter"):
            if authenticate_user(email, password):
                st.session_state.authenticated = True
                st.session_state.user_email = email  # ← IMPORTANT : Sauvegarder l'email
                st.session_state.page = "chat"
                st.success("Connecté avec succès !")
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")

        # Colonnes pour les boutons à gauche/droite
        col1, col2, col3 = st.columns([1, 1.8, 1])  # col2 très étroite pour l'espacement
        with col1:
            if st.button("Mot de passe oublié ?"):
                st.session_state.page = "forgot_password"
                st.rerun()
        with col3:
            if st.button("Créer un compte"):
                st.session_state.page = "signup_email"
                st.rerun()


    elif page == "signup_email":
        # Titre centré "Inscription"
        st.markdown("<h1 style='text-align:center;'>📝 Inscription</h1>", unsafe_allow_html=True)
        # Sous-titre "Étape 1" en plus grand mais pas titre
        st.markdown("<h3 style='text-align:center; margin-bottom: 2rem;'>Étape 1 : Entrez votre email</h3>", unsafe_allow_html=True)

        email = st.text_input("Email")
        if st.button("Envoyer code de vérification"):
            if not is_valid_email(email):
                st.error("Email non autorisé.")
            elif is_email_taken(email):
                st.error("Email déjà utilisé.")
            else:
                if send_verification_code(email, for_reset=False):
                    st.session_state.signup_email = email
                    st.session_state.page = "signup_verify_code"
                    st.success(f"Code envoyé à {email}")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'envoi du code.")
        if st.button("Retour"):
            st.session_state.page = "login"
            st.rerun()

    elif page == "signup_verify_code":
        st.markdown("<h1 style='text-align:center;'>📝Inscription</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom: 2rem;'>Étape 2 : Vérifiez votre email</h3>", unsafe_allow_html=True)

        code = st.text_input("Code de vérification")
        email = st.session_state.get("signup_email", "")
        if st.button("Vérifier code"):
            if verify_code(email, code):
                st.session_state.page = "signup_register_password"
                st.success("Code validé. Choisissez un mot de passe.")
                st.rerun()
            else:
                st.error("Code incorrect ou expiré.")
        if st.button("Retour"):
            st.session_state.page = "signup_email"
            st.rerun()

    elif page == "signup_register_password":
        st.markdown("<h1 style='text-align:center;'>📝 Inscription</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom: 2rem;'>Étape 3 : Choisissez un mot de passe</h3>", unsafe_allow_html=True)

        password = st.text_input("Mot de passe", type="password")
        password_confirm = st.text_input("Confirmez le mot de passe", type="password")
        email = st.session_state.get("signup_email", "")
        if st.button("S'inscrire"):
            if password != password_confirm:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                if register_user(email, password):
                    st.success("Inscription réussie ! Vous pouvez maintenant vous connecter.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("Erreur lors de l'inscription.")
        if st.button("Retour"):
            st.session_state.page = "signup_verify_code"
            st.rerun()
   
    elif page == "forgot_password":
        st.markdown("<h1 style='text-align:center;'>🔁 Mot de passe oublié</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom: 2rem;'>Étape 1 : Entrez votre email</h3>", unsafe_allow_html=True)

        email = st.text_input("Email")
        if st.button("Envoyer code de vérification"):
            if not is_valid_email(email):
                st.error("Email non autorisé.")
            elif not is_email_taken(email):
                st.error("Email inconnu.")
            else:
                if send_verification_code(email, for_reset=True):
                    st.session_state.forgot_email = email
                    st.session_state.page = "forgot_verify_code"
                    st.success(f"Code envoyé à {email}")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'envoi du code.")
        if st.button("Retour"):
            st.session_state.page = "login"
            st.rerun()

    elif page == "forgot_verify_code":
        st.markdown("<h1 style='text-align:center;'>🔁 Mot de passe oublié</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom: 2rem;'>Étape 2 : Vérifiez votre email</h3>", unsafe_allow_html=True)

        code = st.text_input("Code de vérification")
        email = st.session_state.get("forgot_email", "")
        if st.button("Vérifier code"):
            if verify_code(email, code):
                st.session_state.page = "forgot_reset_password"
                st.success("Code validé. Choisissez un nouveau mot de passe.")
                st.rerun()
            else:
                st.error("Code incorrect ou expiré.")
        if st.button("Retour"):
            st.session_state.page = "forgot_password"
            st.rerun()

    elif page == "forgot_reset_password":
        st.markdown("<h1 style='text-align:center;'>🔁 Mot de passe oublié</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; margin-bottom: 2rem;'>Étape 3 : Nouveau mot de passe</h3>", unsafe_allow_html=True)

        password = st.text_input("Nouveau mot de passe", type="password")
        password_confirm = st.text_input("Confirmez le nouveau mot de passe", type="password")
        email = st.session_state.get("forgot_email", "")
        if st.button("Réinitialiser le mot de passe"):
            if password != password_confirm:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                if reset_password(email, password):
                    st.success("Mot de passe réinitialisé avec succès.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("Erreur lors de la réinitialisation.")
        if st.button("Retour"):
            st.session_state.page = "forgot_verify_code"
            st.rerun()