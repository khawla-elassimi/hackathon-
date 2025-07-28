import bcrypt
import random
import string
import smtplib
from pymongo import MongoClient
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from db import *
import os
from dotenv import load_dotenv

# Charger le fichier .env
load_dotenv()

# Récupérer les variables d'environnement
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
ALLOWED_DOMAIN = os.getenv('ALLOWED_DOMAIN')

# ---------------------------
# Validation Email
# ---------------------------
def is_valid_email(email: str) -> bool:
    return email.lower().endswith(ALLOWED_DOMAIN)

# ---------------------------
# Vérifie si l'email est déjà utilisé
# ---------------------------
def is_email_taken(email: str) -> bool:
    user = users.find_one({"email": email})
    # Compte considéré pris si existe et a un mot de passe (compte complet)
    return user is not None and "password_hash" in user

# ---------------------------
# Envoi de code de vérification
# ---------------------------
# for_reset : False = inscription, True = reset mot de passe
def send_verification_code(email: str, for_reset: bool = False) -> bool:
    user = users.find_one({"email": email})

    # Inscription : si email pris, on refuse
    if not for_reset and user and "password_hash" in user:
        return False

    # Reset mot de passe : email inconnu ou sans mot de passe, refuse
    if for_reset and (not user or "password_hash" not in user):
        return False

    # Générer et enregistrer code
    code = ''.join(random.choices(string.digits, k=6))
    verif_col.update_one(
        {"email": email},
        {"$set": {"code": code, "timestamp": datetime.utcnow(), "for_reset": for_reset}},
        upsert=True
    )

    # Préparer email
    message = MIMEText(f"Votre code de vérification est : {code}")
    message["Subject"] = "Code de vérification"
    message["From"] = SMTP_USER
    message["To"] = email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as e:
        print("Erreur d'envoi email:", e)
        return False

# ---------------------------
# Vérifie le code
# ---------------------------
def verify_code(email: str, code: str) -> bool:
    record = verif_col.find_one({"email": email})
    if not record:
        return False

    if record["code"] == code and datetime.utcnow() - record["timestamp"] < timedelta(minutes=10):
        # Pour inscription seulement, on marque l’email comme vérifié ici
        if not record.get("for_reset", False):
            save_verified_email(email)
        # Supprimer le code après usage
        verif_col.delete_one({"email": email})
        return True
    return False

# ---------------------------
# Marquer un email comme vérifié (inscription)
# ---------------------------
def save_verified_email(email: str):
    users.update_one(
        {"email": email},
        {"$setOnInsert": {
            "email": email,
            "verified": True,
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )

# ---------------------------
# Enregistrement mot de passe après vérification (inscription)
# ---------------------------
def register_user(email: str, password: str) -> bool:
    user = users.find_one({"email": email})
    # L’email doit être vérifié et ne pas avoir déjà de mot de passe
    if not user or not user.get("verified", False) or "password_hash" in user:
        return False

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    result = users.update_one(
        {"email": email, "verified": True, "password_hash": {"$exists": False}},
        {"$set": {"password_hash": password_hash}}
    )
    return result.modified_count == 1

# ---------------------------
# Authentification
# ---------------------------
def authenticate_user(email: str, password: str) -> bool:
    user = users.find_one({"email": email})
    if not user or "password_hash" not in user:
        return False
    return bcrypt.checkpw(password.encode(), user["password_hash"])

# ---------------------------
# Réinitialisation du mot de passe
# ---------------------------
def reset_password(email: str, new_password: str) -> bool:
    user = users.find_one({"email": email})
    if not user:
        return False
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    result = users.update_one(
        {"email": email},
        {"$set": {"password_hash": password_hash}}
    )
    return result.modified_count > 0


