import streamlit as st  
import os
import time
import json
from datetime import datetime
from bson import ObjectId
from db import conversations  # collection MongoDB
from agent import RAGAgent, RAGAgentInterface


# Initialisation globale de l'agent RAG (cache pour éviter les reinitialisations)
@st.cache_resource
def init_rag_agent():
    """Initialize RAG Agent with caching"""
    try:
        agent = RAGAgent()
        return agent
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation de l'agent RAG: {str(e)}")
        return None

def format_agent_response(response_data):
    """Formate la réponse de l'agent pour l'affichage"""
    if not response_data:
        return "Aucune réponse reçue.", []
    
    # Gérer différents types de réponses
    if isinstance(response_data, dict):
        if "answer" in response_data:
            return response_data["answer"], response_data.get("sources", [])
        elif "summary" in response_data:
            return response_data["summary"], response_data.get("sources", [])
        elif "analysis" in response_data:
            return response_data["analysis"], response_data.get("sources", [])
        elif "translation" in response_data:
            return f"**Traduction :** {response_data['translation']}", []
        elif "comparison" in response_data:
            return response_data["comparison"], response_data.get("sources1", []) + response_data.get("sources2", [])
        elif "entities" in response_data:
            entities = response_data["entities"]
            if isinstance(entities, dict) and "error" not in entities:
                formatted_entities = []
                for entity_type, entity_list in entities.items():
                    if entity_list:
                        formatted_entities.append(f"**{entity_type.capitalize()}:** {', '.join(entity_list)}")
                return "**Entités extraites :**\n" + "\n".join(formatted_entities), response_data.get("sources", [])
            else:
                return str(entities), []
        elif "results" in response_data:
            results = response_data["results"]
            formatted_results = [f"**Résultats de recherche ({response_data.get('total_found', 0)} trouvés) :**"]
            for i, result in enumerate(results[:5], 1):
                formatted_results.append(f"\n**{i}. Source :** {result['source']}")
                formatted_results.append(f"**Extrait :** {result['content'][:300]}...")
            return "\n".join(formatted_results), [r['source'] for r in results]
        elif "error" in response_data:
            return f"❌ {response_data['error']}", []
        else:
            return str(response_data), []
    else:
        return str(response_data), []

def stream_agent_response(agent, user_input):
    """Simule le streaming de la réponse de l'agent"""
    try:
        # Traiter la demande via l'agent
        full_response_data = agent.process_request(user_input)
        
        # Formater la réponse
        full_response, sources = format_agent_response(full_response_data)
        
        # Simuler le streaming caractère par caractère
        for i in range(len(full_response)):
            yield full_response[:i+1], sources, full_response_data
            
    except Exception as e:
        error_msg = f"❌ Erreur lors du traitement: {str(e)}"
        yield error_msg, [], {"error": str(e)}

def stream_web_response(agent, user_input):
    """Simule le streaming de la réponse basée sur le web"""
    try:
        full_response_data = agent.web_search(user_input)
        full_response = full_response_data.get("answer", "Aucune réponse web trouvée.")
        sources = full_response_data.get("sources", [])
        for i in range(len(full_response)):
            yield full_response[:i+1], sources, full_response_data
    except Exception as e:
        error_msg = f"❌ Erreur lors de la recherche web: {str(e)}"
        yield error_msg, [], {"error": str(e)}

def show_chatbot():
    # Vérifier d'abord l'authentification générale
    if not st.session_state.get("authenticated", False):
        st.error("❌ Erreur d'authentification. Veuillez vous reconnecter.")
        st.session_state["page"] = "login"
        st.rerun()
        return
    
    # Récupérer l'email de l'utilisateur connecté (avec fallback)
    user_email = st.session_state.get("user_email", st.session_state.get("username", "utilisateur_anonyme"))
    
    # Utiliser l'email comme identifiant unique
    user_id = user_email
    
    # Header principal
    st.markdown("<h1 style='text-align: center;'>🤖 FactoryBot - Virtual Assistant</h1>", unsafe_allow_html=True)
    
    # Initialiser l'agent RAG
    agent = init_rag_agent()
    if not agent:
        st.error("❌ Impossible d'initialiser l'agent RAG. Vérifiez la configuration.")
        return
    
    # === SIDEBAR ===
    # Bouton de retour à l'accueil dans la sidebar
    st.sidebar.markdown("## 💬 Conversations précédentes")

    # Nouvelle conversation
    if st.sidebar.button("➕ Nouvelle conversation"):
        st.session_state.chat_history = []
        st.session_state.current_chat_title = f"Session du {datetime.now().strftime('%d/%m %H:%M')}"
        st.rerun()

    # Gestion de la suppression avec confirmation
    if "pending_delete" in st.session_state:
        delete_id = st.session_state["pending_delete"]
        st.sidebar.warning("⚠️ Confirmer la suppression ?")
        col_confirm, col_cancel = st.sidebar.columns(2)
        if col_confirm.button("✅ Oui", key="confirm_delete"):
            try:
                conversations.delete_one({"_id": ObjectId(delete_id)})
                del st.session_state["pending_delete"]
                st.success("Conversation supprimée !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la suppression: {str(e)}")
        if col_cancel.button("❌ Non", key="cancel_delete"):
            del st.session_state["pending_delete"]
            st.rerun()

    # Récupérer et afficher UNIQUEMENT les conversations de l'utilisateur connecté
    try:
        user_conversations = list(conversations.find({"user_id": user_id}).sort("timestamp", -1))
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion à la base de données: {str(e)}")
        user_conversations = []
    
    # Afficher le nombre de conversations
    conv_count = len(user_conversations)
    st.sidebar.markdown(f"**{conv_count}** conversation(s) trouvée(s)")
    
    # Afficher les conversations
    for conv in user_conversations:
        col1, col2 = st.sidebar.columns([0.85, 0.15])
        
        # Bouton pour sélectionner la conversation
        if col1.button(conv["title"], key=f"sel_{conv['_id']}"):
            st.session_state.chat_history = conv["messages"]
            st.session_state.current_chat_title = conv["title"]
            st.rerun()
        
        # Bouton pour supprimer la conversation
        if col2.button("🗑️", key=f"del_{conv['_id']}"):
            st.session_state["pending_delete"] = str(conv["_id"])
            st.rerun()

    # Sidebar avec informations utilisateur fixe en bas
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👤 Utilisateur connecté")
    st.sidebar.markdown(f"**Identifiant:** {user_id}")

    if st.sidebar.button("← Retour à l'accueil"):
        st.session_state["page"] = "accueil"
        st.rerun()
    

    # === ZONE PRINCIPALE DE CHAT ===
    
    # Initialiser l'historique de chat s'il n'existe pas
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("current_chat_title", f"Session du {datetime.now().strftime('%d/%m %H:%M')}")

    # ✅ Initialiser une nouvelle conversation si l'utilisateur vient de se connecter
    if "just_logged_in" in st.session_state:
        # Vider l'historique au premier chargement après login
        st.session_state.chat_history = []
        st.session_state.current_chat_title = f"Session du {datetime.now().strftime('%d/%m %H:%M')}"
        del st.session_state["just_logged_in"]  # Supprimer le flag après utilisation

    # Affichage des messages existants
    for idx, msg in enumerate(st.session_state.chat_history):
        avatar = "👤" if msg["role"] == "user" else "🤖"
        align = "flex-end" if msg["role"] == "user" else "flex-start"
        bubble_color = "#e0f7fa" if msg["role"] == "user" else "#e8f5e9"

        st.markdown(
            f"""
            <div style='display: flex; justify-content: {align}; margin-bottom: 10px;'>
                {"<div style='background-color: " + bubble_color + "; padding: 16px; border-radius: 12px; max-width: 95%; font-size: 0.9rem;'>" + msg["content"] + "</div><div style='margin-left: 8px; font-size: 1.5rem;'>" + avatar + "</div>"
                 if msg["role"] == "user" else 
                 "<div style='margin-right: 8px; font-size: 1.5rem;'>" + avatar + "</div><div style='background-color: " + bubble_color + "; padding: 16px; border-radius: 12px; max-width: 95%; font-size: 0.9rem;'>" + msg["content"].replace('\n', '<br>') + "</div>"}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Afficher les sources si disponibles (sans le paramètre key)
        if msg.get("sources"):
            with st.expander(f"📄 Sources utilisées ({len(msg['sources'])} sources)"):
                for i, source in enumerate(msg["sources"]):
                    file_path = os.path.join("DB", source)  # Utiliser toujours le dossier DB
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📥 Télécharger {source}",
                                data=f,
                                file_name=source,
                                mime="application/octet-stream",
                                key=f"download_{idx}_{i}"
                            )
                    else:
                        st.write(f"• {source} (fichier introuvable)")
        
        # Afficher les métadonnées de l'agent si disponibles
        if msg.get("agent_metadata"):
            metadata = msg["agent_metadata"]
            if metadata.get("execution_time"):
                st.caption(f"⏱️ Temps d'exécution: {metadata['execution_time']:.2f}s | Confiance: {metadata.get('confidence', 0):.2f}")

    # === ZONE DE SAISIE ===
    st.markdown("---")

    # Zone de saisie principale
    with st.form("formulaire_question", clear_on_submit=True):
        user_input = st.text_input("Posez votre question :", "")
        use_web = st.checkbox("🔎 Utiliser la recherche web", value=False)
        submitted = st.form_submit_button("Envoyer")

    if submitted and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        st.markdown("---")
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-end; margin-bottom: 10px;'>
                <div style='background-color: #e0f7fa; padding: 16px; border-radius: 12px; max-width: 95%; font-size: 0.9rem;'>{user_input}</div>
                <div style='margin-left: 8px; font-size: 1.5rem;'>👤</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Conteneur pour la réponse en streaming
        response_container = st.empty()
        st.markdown(
            """
            <div style='display: flex; justify-content: flex-start; margin-bottom: 10px;'>
                <div style='margin-right: 8px; font-size: 1.5rem;'>🤖</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        full_response = ""
        sources = []
        agent_metadata = {}

        with st.spinner("🧠 FactoryBot Agent traite votre demande..."):
            try:
                if use_web:
                    for current_response, current_sources, response_data in stream_web_response(agent, user_input):
                        full_response = current_response
                        sources = current_sources
                        response_container.markdown(
                            f"""
                            <div style='background-color: #e8f5e9; padding: 16px; border-radius: 12px; max-width: 95%; font-size: 0.9rem; margin-left: 40px;'>
                                {full_response.replace(chr(10), '<br>')}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        time.sleep(0.02)
                else:
                    for current_response, current_sources, response_data in stream_agent_response(agent, user_input):
                        full_response = current_response
                        sources = current_sources
                        if isinstance(response_data, dict):
                            agent_metadata = {
                                "execution_time": response_data.get("execution_time", 0),
                                "confidence": response_data.get("confidence", 0),
                                "task_id": response_data.get("task_id", ""),
                                "session_id": response_data.get("session_id", "")
                            }
                        response_container.markdown(
                            f"""
                            <div style='background-color: #e8f5e9; padding: 16px; border-radius: 12px; max-width: 95%; font-size: 0.9rem; margin-left: 40px;'>
                                {full_response.replace(chr(10), '<br>')}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        time.sleep(0.02)
            except Exception as e:
                st.error(f"❌ Erreur lors du traitement par l'agent: {str(e)}")
                full_response = "Désolé, une erreur s'est produite lors du traitement de votre demande."
                sources = []

        # Ajouter la réponse à l'historique avec métadonnées
        assistant_message = {
            "role": "assistant",
            "content": full_response,
            "sources": sources,
            "agent_metadata": agent_metadata
        }
        st.session_state.chat_history.append(assistant_message)

        # Affichage des sources
        if sources:
            with st.expander(f"📄 Sources utilisées par l'agent ({len(sources)} sources)"):
                st.markdown("**L'agent a consulté les documents suivants :**")
                for i, source in enumerate(sources):
                    file_path = os.path.join("DB", source)
                    if os.path.exists(file_path):
                        col1, col2 = st.columns([3, 1])
                        col1.write(f"📄 {source}")
                        with open(file_path, "rb") as f:
                            col2.download_button(
                                label="📥 Télécharger",
                                data=f,
                                file_name=source,
                                mime="application/octet-stream",
                                key=f"download_stream_{i}"
                            )
                    else:
                        st.write(f"• {source} ⚠️ (fichier introuvable)")

        # Affichage des métadonnées de performance
        if agent_metadata.get("execution_time"):
            st.info(f"⏱️ Traitement effectué en {agent_metadata['execution_time']:.2f}s | "
                   f"Confiance: {agent_metadata.get('confidence', 0):.0%} | "
                   f"Task ID: {agent_metadata.get('task_id', 'N/A')[:8]}...")

        # Sauvegarder la conversation avec l'EMAIL comme user_id
        try:
            conversations.delete_many({"user_id": user_id, "title": st.session_state.current_chat_title})
            conversations.insert_one({
                "user_id": user_id,
                "title": st.session_state.current_chat_title,
                "timestamp": datetime.now(),
                "messages": st.session_state.chat_history,
                "agent_version": "RAG_Agent_v2",
                "total_messages": len(st.session_state.chat_history)
            })
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")

        time.sleep(0.5)
        st.rerun()
# ...existing code...

# Point d'entrée principal si ce fichier est exécuté directement
if __name__ == "__main__":
    show_chatbot()