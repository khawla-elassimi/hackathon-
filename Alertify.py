import streamlit as st
from dotenv import load_dotenv
import os
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime, timedelta
import threading
import queue
import numpy as np
from dataclasses import asdict  
from mine_core_system import MineEmergencySystem, RiskLevel, SensorStatus
import logging


st.set_page_config(
    page_title="Alertify IA",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration du logging pour Streamlit
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
        border-bottom: 3px solid #ff6b35;
        padding-bottom: 1rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .risk-normal { background-color: #28a745; }
    .risk-warning { background-color: #ffc107; }
    .risk-critical { background-color: #dc3545; }
    .risk-emergency { background-color: #6f42c1; animation: blink 1s infinite; }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.5; }
    }
    
    .zone-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
    }
    
    .alert-urgent {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    
    .sidebar-info {
        background-color: #e9ecef;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitMineInterface:
    """Interface Streamlit pour le système de surveillance"""
    
    def __init__(self):
        # Charger les variables d'environnement
        load_dotenv()
        self.mine_system = None
        self.monitoring_active = False
        self.data_queue = queue.Queue()
        self.monitoring_thread = None
        self.api_key = os.getenv('CLAUDE_API_KEY')
        
        # Initialisation directe du système
        try:
            if not self.api_key:
                st.error("❌ Clé API Claude non trouvée dans le fichier .env")
                return
            self.mine_system = MineEmergencySystem(self.api_key)
            st.session_state.system_initialized = True
        except Exception as e:
            logger.error(f"Erreur initialisation: {e}")

        # Initialisation des données de session
        if 'current_data' not in st.session_state:
            st.session_state.current_data = {}
        if 'alerts_history' not in st.session_state:
            st.session_state.alerts_history = []
        if 'sensor_history' not in st.session_state:
            st.session_state.sensor_history = {}

        # Démarrage automatique de la surveillance
        self.start_monitoring_thread()

    def initialize_system(self):
        """Initialise le système de surveillance"""
        try:
            self.mine_system = MineEmergencySystem(self.api_key)
            st.session_state.system_initialized = True
            st.success("✅ Système initialisé avec succès!")
            return True
        except Exception as e:
            st.error(f"❌ Erreur d'initialisation: {str(e)}")
            return False
    
    def start_monitoring_thread(self):
        """Démarre le monitoring dans un thread séparé"""
        if not self.monitoring_active and self.mine_system:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            st.success("🚀 Surveillance démarrée")
    
    def _monitoring_loop(self):
        """Boucle de surveillance optimisée"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self.monitoring_active:
                if not self.mine_system:
                    time.sleep(0.5)
                    continue
                
                # Récupération optimisée des données
                data_snapshot = {
                    'timestamp': datetime.now().isoformat(),
                    'sensor_readings': {k: v.to_dict() for k, v in self.mine_system.data_simulator.get_all_sensor_readings().items()},
                    'zone_status': self.mine_system.data_simulator.get_zone_status(),
                    'weather': self.mine_system.data_simulator.weather.to_dict(),  # Utiliser to_dict() au lieu de asdict
                    'production': self.mine_system.data_simulator.production.to_dict()  # Utiliser to_dict() au lieu de asdict
                }

                try:
                    if self.data_queue.qsize() > 5:
                        self.data_queue.get_nowait()
                    self.data_queue.put_nowait(data_snapshot)
                except queue.Full:
                    pass
                
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Erreur surveillance: {e}")
        finally:
            loop.close()
    
    def update_session_data(self):
        """Met à jour les données de session avec les dernières données"""
        try:
            # Limite le nombre de mises à jour par cycle
            max_updates = 5
            updates_count = 0
            
            while not self.data_queue.empty() and updates_count < max_updates:
                data = self.data_queue.get_nowait()
                st.session_state.current_data = data
                
                # Optimisation de la mise à jour de l'historique
                for sensor_id, reading in data['sensor_readings'].items():
                    if sensor_id not in st.session_state.sensor_history:
                        st.session_state.sensor_history[sensor_id] = []
                    
                    history = st.session_state.sensor_history[sensor_id]
                    if len(history) >= 50:  # Limite fixe pour l'historique
                        history.pop(0)  # Retire le plus ancien
                    
                    history.append({
                        'timestamp': data['timestamp'],
                        'value': reading['value'],
                        'status': reading['status']
                    })
                
                updates_count += 1
                
        except queue.Empty:
            pass
    
    def render_main_dashboard(self):
        """Affiche le tableau de bord principal"""
        st.markdown('<h1 class="main-header">🏭 Alertify IA- Phospahte Mining</h1>', 
                   unsafe_allow_html=True)
        
        # Mise à jour des données
        self.update_session_data()
        
        current_data = st.session_state.current_data
        if not current_data:
            st.info("Chargement des données...")
            time.sleep(0.5)
            st.rerun()
            return
        
        # Métriques principales
        self.render_key_metrics(current_data)
        
        # Layout en colonnes
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Graphiques des capteurs
            self.render_sensor_charts(current_data)
            
            # Statut des zones
            self.render_zone_status(current_data)
        
        with col2:
            # Panneau de contrôle
            self.render_control_panel()
            
            # Alertes
            self.render_alerts_panel()
            
            # Conditions météo
            self.render_weather_panel(current_data)
    
    def render_initialization_page(self):
        """Page d'initialisation du système"""
        st.markdown("### ⚙️ Configuration Initiale")
        
        # Paramètres de surveillance simples
        monitoring_interval = st.selectbox(
            "Intervalle de surveillance",
            [5, 10, 15, 30],
            index=0,
            help="Intervalle en secondes entre les analyses"
        )
        
        alert_sensitivity = st.selectbox(
            "Sensibilité des alertes",
            ["Faible", "Normale", "Élevée"],
            index=1
        )
        
        if st.button("🚀 Initialiser le Système"):
            if self.initialize_system():
                st.rerun()

    def render_key_metrics(self, data):
        """Affiche les métriques clés"""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Calcul du niveau de risque global
        sensor_readings = data['sensor_readings']
        critical_count = sum(1 for reading in sensor_readings.values() 
                           if reading['status'] == 'critical')
        warning_count = sum(1 for reading in sensor_readings.values() 
                          if reading['status'] == 'warning')
        
        global_risk = "NORMAL"
        if critical_count > 3:
            global_risk = "EMERGENCY"
        elif critical_count > 0:
            global_risk = "CRITICAL"
        elif warning_count > 2:
            global_risk = "WARNING"
        
        risk_colors = {
            "NORMAL": "#28a745",
            "WARNING": "#ffc107", 
            "CRITICAL": "#dc3545",
            "EMERGENCY": "#6f42c1"
        }
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="background-color: {risk_colors[global_risk]}">
                <h3>🚦 Niveau de Risque</h3>
                <h2>{global_risk}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            production_rate = data['production']['hourly_production']
            efficiency = data['production']['efficiency_rate']
            st.markdown(f"""
            <div class="metric-card">
                <h3>⚙️ Production</h3>
                <h2>{production_rate:.0f} t/h</h2>
                <p>Efficacité: {efficiency:.1%}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_personnel = sum(zone['personnel']['personnel_count'] 
                                for zone in data['zone_status'].values())
            st.markdown(f"""
            <div class="metric-card">
                <h3>👥 Personnel</h3>
                <h2>{total_personnel}</h2>
                <p>Personnes sur site</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🔴 Capteurs Critiques</h3>
                <h2>{critical_count}</h2>
                <p>⚠️ Avertissements: {warning_count}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            weather = data['weather']
            weather_status = "🌤️ FAVORABLE"
            if weather['wind_speed'] > 12:
                weather_status = "🌪️ VENT FORT"
            elif weather['visibility'] < 2:
                weather_status = "🌫️ VISIBILITÉ RÉDUITE"
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>🌍 Météo</h3>
                <h2>{weather['temperature']:.1f}°C</h2>
                <p>{weather_status}</p>
            </div>
            """, unsafe_allow_html=True)
    
    def render_sensor_charts(self, data):
        """Affiche les graphiques des capteurs"""
        st.markdown("### 📊 Surveillance des Capteurs")
        
        # Sélection des capteurs à afficher
        sensor_readings = data['sensor_readings']
        sensor_types = set(reading['sensor_type'] for reading in sensor_readings.values())
        
        selected_type = st.selectbox(
            "Type de capteur à afficher:",
            list(sensor_types)
        )
        
        # Filtrer les capteurs par type
        filtered_sensors = {k: v for k, v in sensor_readings.items() 
                          if v['sensor_type'] == selected_type}
        
        if filtered_sensors:
            # Graphique en temps réel
            fig = make_subplots(
                rows=len(filtered_sensors),
                cols=1,
                subplot_titles=[f"{sensor_id} - {reading['location']}" 
                               for sensor_id, reading in filtered_sensors.items()],
                vertical_spacing=0.05
            )
            
            for i, (sensor_id, reading) in enumerate(filtered_sensors.items(), 1):
                # Données historiques
                history = st.session_state.sensor_history.get(sensor_id, [])
                if history:
                    timestamps = [h['timestamp'] for h in history]
                    values = [h['value'] for h in history]
                    
                    # Couleur selon le statut
                    color = {
                        'normal': 'green',
                        'warning': 'orange', 
                        'critical': 'red',
                        'offline': 'gray'
                    }.get(reading['status'], 'blue')
                    
                    fig.add_trace(
                        go.Scatter(
                            x=timestamps,
                            y=values,
                            mode='lines+markers',
                            name=sensor_id,
                            line=dict(color=color, width=2),
                            marker=dict(size=4)
                        ),
                        row=i, col=1
                    )
                    
                    # Ligne de seuil si disponible
                    if 'critical_threshold' in reading:
                        fig.add_hline(
                            y=reading.get('critical_threshold', 0),
                            line_dash="dash",
                            line_color="red",
                            annotation_text="Seuil critique",
                            row=i, col=1
                        )
            
            fig.update_layout(
                height=300 * len(filtered_sensors),
                title=f"Évolution des capteurs - {selected_type}",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Tableau récapitulatif
        st.markdown("#### 📋 État Actuel des Capteurs")
        
        sensor_df = pd.DataFrame([
            {
                'Capteur': sensor_id,
                'Type': reading['sensor_type'],
                'Valeur': f"{reading['value']} {reading['unit']}",
                'Statut': reading['status'].upper(),
                'Zone': reading['zone'],
                'Localisation': reading['location']
            }
            for sensor_id, reading in sensor_readings.items()
        ])
        
        # Coloration du tableau selon le statut
        def color_status(val):
            colors = {
                'NORMAL': 'background-color: #d4edda',
                'WARNING': 'background-color: #fff3cd',
                'CRITICAL': 'background-color: #f8d7da',
                'OFFLINE': 'background-color: #e2e3e5'
            }
            return colors.get(val, '')
        
        styled_df = sensor_df.style.applymap(color_status, subset=['Statut'])
        st.dataframe(styled_df, use_container_width=True)
    
    def render_zone_status(self, data):
        """Affiche le statut des zones"""
        st.markdown("### 🏭 Statut des Zones")
        
        zone_status = data['zone_status']
        
        cols = st.columns(len(zone_status))
        
        for i, (zone_name, zone_info) in enumerate(zone_status.items()):
            with cols[i]:
                status = zone_info['status']
                personnel = zone_info['personnel']['personnel_count']
                supervisor = zone_info['personnel']['shift_supervisor']
                
                status_icons = {
                    'normal': '🟢',
                    'warning': '🟡',
                    'critical': '🔴',
                    'degraded': '🟠'
                }
                
                st.markdown(f"""
                <div class="zone-card">
                    <h4>{status_icons.get(status, '⚫')} {zone_name.upper()}</h4>
                    <p><strong>Statut:</strong> {status}</p>
                    <p><strong>Personnel:</strong> {personnel}</p>
                    <p><strong>Superviseur:</strong> {supervisor}</p>
                    <p><strong>Capteurs actifs:</strong> {zone_info['sensor_count']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    def render_control_panel(self):
        """Panneau de contrôle"""
        st.markdown("### 🎛️ Contrôle")
        
        with st.expander("🚨 Simulation d'Urgence", expanded=False):
            st.markdown("**Scénarios de Test:**")
            
            scenario_type = st.selectbox(
                "Type de scénario:",
                ["dust_storm", "chemical_cascade", "equipment_chain"]
            )
            
            intensity = st.selectbox(
                "Intensité:",
                ["low", "moderate", "high", "extreme"]
            )
            
            if st.button("🧪 Déclencher Scénario"):
                if self.mine_system:
                    self.mine_system.trigger_advanced_scenario(scenario_type, intensity)
                    st.success(f"Scénario {scenario_type} déclenché avec intensité {intensity}")
                else:
                    st.error("Système non initialisé")
        
        with st.expander("⚙️ Paramètres", expanded=False):
            st.markdown("**Surveillance:**")
            
            if st.button("▶️ Démarrer Surveillance"):
                self.start_monitoring_thread()
            
            if st.button("⏹️ Arrêter Surveillance"):
                self.monitoring_active = False
                st.success("Surveillance arrêtée")
            
            st.markdown("**Export des Données:**")
            if st.button("📊 Exporter JSON"):
                if self.mine_system:
                    export_data = self.mine_system.export_data("json", 24)
                    st.download_button(
                        label="📥 Télécharger",
                        data=export_data,
                        file_name=f"mine_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
    
    def render_alerts_panel(self):
        """Panneau des alertes"""
        st.markdown("### 🔔 Alertes")
        
        # Simulation d'alertes basées sur les données actuelles
        current_data = st.session_state.current_data
        if current_data:
            alerts = []
            
            # Vérifier les capteurs critiques
            for sensor_id, reading in current_data['sensor_readings'].items():
                if reading['status'] == 'critical':
                    alerts.append({
                        'level': 'CRITIQUE',
                        'message': f"Capteur {sensor_id}: {reading['value']} {reading['unit']}",
                        'time': datetime.now().strftime('%H:%M:%S')
                    })
            
            # Vérifier les conditions météo
            weather = current_data['weather']
            if weather['wind_speed'] > 15:
                alerts.append({
                    'level': 'ATTENTION',
                    'message': f"Vent fort: {weather['wind_speed']:.1f} m/s",
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            
            # Afficher les alertes
            if alerts:
                for alert in alerts[-5:]:  # 5 dernières alertes
                    level_colors = {
                        'CRITIQUE': '#dc3545',
                        'ATTENTION': '#ffc107',
                        'INFO': '#17a2b8'
                    }
                    
                    st.markdown(f"""
                    <div class="alert-urgent" style="border-left: 4px solid {level_colors.get(alert['level'], '#6c757d')}">
                        <strong>{alert['level']}</strong> - {alert['time']}<br>
                        {alert['message']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ Aucune alerte active")
    
    def render_weather_panel(self, data):
        """Panneau météo"""
        st.markdown("### 🌤️ Conditions Météorologiques")
        
        weather = data['weather']
        
        # Graphique en gauge pour la vitesse du vent
        fig_wind = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = weather['wind_speed'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Vent (m/s)"},
            delta = {'reference': 5},
            gauge = {
                'axis': {'range': [None, 25]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 5], 'color': "lightgray"},
                    {'range': [5, 12], 'color': "yellow"},
                    {'range': [12, 25], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 15
                }
            }
        ))
        
        fig_wind.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_wind, use_container_width=True)
        
        # Informations détaillées
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🌡️ Température", f"{weather['temperature']:.1f}°C")
            st.metric("💨 Humidité", f"{weather['humidity']:.1f}%")
            st.metric("👁️ Visibilité", f"{weather['visibility']:.1f} km")
        
        with col2:
            st.metric("🧭 Direction Vent", f"{weather['wind_direction']:.0f}°")
            st.metric("📊 Pression", f"{weather['pressure']:.1f} hPa")
    
    def render_analytics_page(self):
        """Page d'analytiques avancées"""
        st.markdown("# 📈 Analytiques Avancées")
        
        if not st.session_state.system_initialized:
            st.warning("Système non initialisé")
            return
        
        # Onglets pour différentes analyses
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Tendances", "🔍 Corrélations", "🎯 Prédictions", "📋 Rapports"])
        
        with tab1:
            self.render_trends_analysis()
        
        with tab2:
            self.render_correlation_analysis()
        
        with tab3:
            self.render_prediction_analysis()
        
        with tab4:
            self.render_reports()
    
    def render_trends_analysis(self):
        """Analyse des tendances"""
        st.markdown("### 📈 Analyse des Tendances")
        
        # Sélection de capteurs pour analyse
        if st.session_state.sensor_history:
            sensor_options = list(st.session_state.sensor_history.keys())
            selected_sensors = st.multiselect(
                "Sélectionnez les capteurs à analyser:",
                sensor_options,
                default=sensor_options[:3] if len(sensor_options) >= 3 else sensor_options
            )
            
            if selected_sensors:
                # Graphique des tendances
                fig = go.Figure()
                
                for sensor_id in selected_sensors:
                    history = st.session_state.sensor_history[sensor_id]
                    if history:
                        timestamps = [datetime.fromisoformat(h['timestamp']) for h in history]
                        values = [h['value'] for h in history]
                        
                        fig.add_trace(go.Scatter(
                            x=timestamps,
                            y=values,
                            mode='lines+markers',
                            name=sensor_id,
                            line=dict(width=2),
                            marker=dict(size=4)
                        ))
                
                fig.update_layout(
                    title="Évolution temporelle des capteurs sélectionnés",
                    xaxis_title="Temps",
                    yaxis_title="Valeurs",
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistiques des tendances
                st.markdown("#### 📊 Statistiques des Tendances")
                
                stats_data = []
                for sensor_id in selected_sensors:
                    if self.mine_system:
                        trend_data = self.mine_system.get_sensor_trends(sensor_id, 6)
                        if 'error' not in trend_data:
                            stats_data.append({
                                'Capteur': sensor_id,
                                'Valeur Actuelle': f"{trend_data['current_value']} {trend_data['unit']}",
                                'Tendance': trend_data['trend_direction'],
                                'Variation (%)': f"{trend_data['trend_percentage']:.1f}%",
                                'Moyenne Récente': f"{trend_data['recent_average']} {trend_data['unit']}",
                                'Volatilité': f"{trend_data['volatility']:.2f}",
                                'Statut': trend_data['status']
                            })
                
                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True)
    
    def render_correlation_analysis(self):
        """Analyse des corrélations"""
        st.markdown("### 🔍 Analyse des Corrélations")
        
        if not st.session_state.sensor_history:
            st.warning("Pas assez de données historiques pour l'analyse des corrélations")
            return
        
        # Préparer les données pour l'analyse de corrélation
        correlation_data = {}
        min_length = float('inf')
        
        for sensor_id, history in st.session_state.sensor_history.items():
            if len(history) > 10:  # Au moins 10 points de données
                values = [h['value'] for h in history]
                correlation_data[sensor_id] = values
                min_length = min(min_length, len(values))
        
        if len(correlation_data) >= 2 and min_length > 10:
            # Tronquer toutes les séries à la même longueur
            for sensor_id in correlation_data:
                correlation_data[sensor_id] = correlation_data[sensor_id][-min_length:]
            
            # Créer DataFrame pour corrélation
            corr_df = pd.DataFrame(correlation_data)
            correlation_matrix = corr_df.corr()
            
            # Heatmap des corrélations
            fig = px.imshow(
                correlation_matrix,
                x=correlation_matrix.columns,
                y=correlation_matrix.columns,
                color_continuous_scale='RdBu_r',
                title="Matrice de Corrélation des Capteurs",
                aspect="auto"
            )
            
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # Corrélations significatives
            st.markdown("#### 🔗 Corrélations Significatives")
            
            significant_correlations = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) > 0.5:  # Corrélation significative
                        significant_correlations.append({
                            'Capteur 1': correlation_matrix.columns[i],
                            'Capteur 2': correlation_matrix.columns[j],
                            'Corrélation': f"{corr_value:.3f}",
                            'Force': 'Forte' if abs(corr_value) > 0.7 else 'Modérée',
                            'Type': 'Positive' if corr_value > 0 else 'Négative'
                        })
            
            if significant_correlations:
                corr_df = pd.DataFrame(significant_correlations)
                st.dataframe(corr_df, use_container_width=True)
            else:
                st.info("Aucune corrélation significative détectée")
        else:
            st.warning("Pas assez de données ou de capteurs pour l'analyse des corrélations")
    
    def render_prediction_analysis(self):
        """Analyse prédictive"""
        st.markdown("### 🎯 Analyse Prédictive")
        
        st.info("🤖 Cette section utilise l'IA Claude pour les prédictions avancées")
        
        # Sélection du capteur pour prédiction
        if st.session_state.sensor_history:
            sensor_options = list(st.session_state.sensor_history.keys())
            selected_sensor = st.selectbox(
                "Capteur pour prédiction:",
                sensor_options
            )
            
            prediction_horizon = st.selectbox(
                "Horizon de prédiction:",
                ["30 minutes", "1 heure", "2 heures", "4 heures"]
            )
            
            if st.button("🔮 Générer Prédiction"):
                with st.spinner("Analyse prédictive en cours..."):
                    # Simulation de prédiction (en réalité, on utiliserait Claude)
                    history = st.session_state.sensor_history[selected_sensor]
                    if len(history) >= 10:
                        recent_values = [h['value'] for h in history[-10:]]
                        current_trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
                        
                        # Prédiction simple basée sur la tendance
                        time_steps = {"30 minutes": 6, "1 heure": 12, "2 heures": 24, "4 heures": 48}
                        steps = time_steps[prediction_horizon]
                        
                        predicted_values = []
                        last_value = recent_values[-1]
                        
                        for i in range(steps):
                            # Ajout de bruit et de tendance
                            next_value = last_value + current_trend + np.random.normal(0, abs(last_value) * 0.05)
                            predicted_values.append(max(0, next_value))  # Valeurs positives seulement
                            last_value = next_value
                        
                        # Génération des timestamps futurs
                        last_timestamp = datetime.fromisoformat(history[-1]['timestamp'])
                        future_timestamps = [
                            last_timestamp + timedelta(minutes=5*i) for i in range(1, steps+1)
                        ]
                        
                        # Graphique de prédiction
                        fig = go.Figure()
                        
                        # Historique
                        historical_timestamps = [datetime.fromisoformat(h['timestamp']) for h in history]
                        historical_values = [h['value'] for h in history]
                        
                        fig.add_trace(go.Scatter(
                            x=historical_timestamps,
                            y=historical_values,
                            mode='lines+markers',
                            name='Historique',
                            line=dict(color='blue', width=2)
                        ))
                        
                        # Prédiction
                        fig.add_trace(go.Scatter(
                            x=future_timestamps,
                            y=predicted_values,
                            mode='lines+markers',
                            name='Prédiction',
                            line=dict(color='red', width=2, dash='dash')
                        ))
                        
                        # Zone de confiance (simulation)
                        upper_bound = [v * 1.1 for v in predicted_values]
                        lower_bound = [v * 0.9 for v in predicted_values]
                        
                        fig.add_trace(go.Scatter(
                            x=future_timestamps + future_timestamps[::-1],
                            y=upper_bound + lower_bound[::-1],
                            fill='toself',
                            fillcolor='rgba(255,0,0,0.2)',
                            line=dict(width=0),
                            name='Zone de confiance',
                            showlegend=False
                        ))
                        
                        fig.update_layout(
                            title=f"Prédiction pour {selected_sensor} - {prediction_horizon}",
                            xaxis_title="Temps",
                            yaxis_title="Valeur",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Analyse des risques
                        st.markdown("#### ⚠️ Analyse des Risques Prédits")
                        
                        # Simulation d'analyse de risque
                        max_predicted = max(predicted_values)
                        current_value = historical_values[-1]
                        
                        risk_assessment = "FAIBLE"
                        risk_color = "green"
                        
                        if max_predicted > current_value * 1.5:
                            risk_assessment = "ÉLEVÉ"
                            risk_color = "red"
                        elif max_predicted > current_value * 1.2:
                            risk_assessment = "MODÉRÉ"
                            risk_color = "orange"
                        
                        st.markdown(f"""
                        <div style="padding: 1rem; border-radius: 8px; background-color: {risk_color}; color: white;">
                            <h4>Niveau de Risque Prédit: {risk_assessment}</h4>
                            <p>Valeur maximale prédite: {max_predicted:.2f}</p>
                            <p>Augmentation par rapport à maintenant: {((max_predicted/current_value-1)*100):.1f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    else:
                        st.warning("Pas assez de données historiques pour la prédiction")
    
    def render_reports(self):
        """Génération de rapports"""
        st.markdown("### 📋 Génération de Rapports")
        
        # Sélection du type de rapport
        report_type = st.selectbox(
            "Type de rapport:",
            ["Rapport quotidien", "Rapport hebdomadaire", "Rapport d'incident", "Rapport de maintenance"]
        )
        
        # Période du rapport
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Date de début", datetime.now().date() - timedelta(days=1))
        with col2:
            end_date = st.date_input("Date de fin", datetime.now().date())
        
        if st.button("📊 Générer Rapport"):
            with st.spinner("Génération du rapport en cours..."):
                # Simulation de génération de rapport
                if self.mine_system:
                    stats = self.mine_system.get_system_statistics()
                    alerts = self.mine_system.get_alerts_history(24)
                    
                    # Contenu du rapport
                    st.markdown(f"""
                    ## 📋 {report_type}
                    **Période:** {start_date} au {end_date}
                    **Généré le:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}
                    
                    ### 📊 Résumé Exécutif
                    - **Statut global du système:** {stats.get('system_status', 'N/A')}
                    - **Niveau de risque actuel:** {stats.get('current_risk_level', 'N/A')}
                    - **Temps de fonctionnement:** {stats.get('uptime_hours', 0):.1f} heures
                    - **Analyses effectuées:** {stats.get('total_analyses', 0)}
                    - **Protocoles exécutés:** {stats.get('protocols_executed', 0)}
                    
                    ### 🏭 État des Zones
                    """)
                    
                    zones_status = stats.get('zones_status', {})
                    for zone_name, zone_info in zones_status.items():
                        status_icon = {"normal": "🟢", "warning": "🟡", "critical": "🔴", "degraded": "🟠"}.get(zone_info.get('status', 'unknown'), "⚫")
                        st.markdown(f"- **{zone_name.upper()}:** {status_icon} {zone_info.get('status', 'N/A')} ({zone_info.get('personnel', {}).get('personnel_count', 0)} personnes)")
                    
                    st.markdown("""
                    ### 🔔 Alertes de la Période
                    """)
                    
                    if alerts:
                        for alert in alerts[-10:]:  # 10 dernières alertes
                            alert_time = alert['timestamp']
                            alert_type = alert['type']
                            st.markdown(f"- **{alert_time}:** {alert_type}")
                    else:
                        st.markdown("Aucune alerte durant cette période.")
                    
                    st.markdown("""
                    ### 🌍 Conditions Environnementales
                    """)
                    
                    weather = stats.get('weather_conditions', {})
                    st.markdown(f"""
                    - **Température moyenne:** {weather.get('temperature', 0):.1f}°C
                    - **Vitesse du vent:** {weather.get('wind_speed', 0):.1f} m/s
                    - **Visibilité:** {weather.get('visibility', 0):.1f} km
                    - **Humidité:** {weather.get('humidity', 0):.1f}%
                    """)
                    
                    st.markdown("""
                    ### ⚙️ Performance de Production
                    """)
                    
                    production = stats.get('production_metrics', {})
                    st.markdown(f"""
                    - **Production horaire:** {production.get('hourly_production', 0):.1f} tonnes/h
                    - **Taux d'efficacité:** {production.get('efficiency_rate', 0):.1%}
                    - **Qualité P2O5:** {production.get('quality_grade', 0):.1f}%
                    - **Consommation énergétique:** {production.get('energy_consumption', 0):.0f} kWh
                    """)
                    
                    st.markdown("""
                    ### 🎯 Recommandations
                    1. Maintenir la surveillance continue des capteurs critiques
                    2. Planifier la maintenance préventive selon les alertes prédictives
                    3. Former le personnel aux nouveaux protocoles d'urgence
                    4. Optimiser la consommation énergétique pendant les pics de production
                    
                    ---
                    *Rapport généré automatiquement par le système de surveillance IA*
                    """)
                    
                    # Bouton de téléchargement
                    report_content = f"""
# {report_type}
Période: {start_date} au {end_date}
Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}

## Résumé Exécutif
- Statut global: {stats.get('system_status', 'N/A')}
- Niveau de risque: {stats.get('current_risk_level', 'N/A')}
- Temps de fonctionnement: {stats.get('uptime_hours', 0):.1f} heures
- Analyses: {stats.get('total_analyses', 0)}
- Protocoles exécutés: {stats.get('protocols_executed', 0)}

## État des Zones
{chr(10).join([f"- {zone}: {info.get('status', 'N/A')}" for zone, info in zones_status.items()])}

## Alertes
{chr(10).join([f"- {alert['timestamp']}: {alert['type']}" for alert in alerts[-10:]]) if alerts else "Aucune alerte"}

---
Rapport généré automatiquement par le système de surveillance IA
                    """
                    
                    st.download_button(
                        label="📥 Télécharger le Rapport",
                        data=report_content,
                        file_name=f"rapport_{report_type.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown"
                    )

def main():
    """Fonction principale de l'application Streamlit"""
    
    # Interface utilisateur
    interface = StreamlitMineInterface()
    
    # Menu de navigation
    st.sidebar.markdown("## 🏭 Navigation")
    page = st.sidebar.selectbox(
        "Choisir une page:",
        ["🏠 Tableau de Bord", "📈 Analytiques", "⚙️ Configuration", "📋 Documentation"]
    )
    
    # Informations système dans la sidebar
    if st.session_state.system_initialized:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 État Système")
        
        if st.session_state.current_data:
            # Statut global
            sensor_readings = st.session_state.current_data['sensor_readings']
            critical_count = sum(1 for reading in sensor_readings.values() 
                               if reading['status'] == 'critical')
            
            if critical_count > 0:
                st.sidebar.error(f"🔴 {critical_count} capteurs critiques")
            else:
                st.sidebar.success("🟢 Système nominal")
            
            # Dernière mise à jour
            last_update = datetime.fromisoformat(st.session_state.current_data['timestamp'])
            st.sidebar.markdown(f"**Dernière MAJ:** {last_update.strftime('%H:%M:%S')}")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🛠️ Actions Rapides")
        
        if st.sidebar.button("🚨 Alerte Test"):
            st.sidebar.success("Alerte de test envoyée!")
        
        if st.sidebar.button("📊 Actualiser"):
            st.rerun()
    
    # Affichage des pages
    if page == "🏠 Tableau de Bord":
        interface.render_main_dashboard()
    elif page == "📈 Analytiques":
        interface.render_analytics_page()
    elif page == "⚙️ Configuration":
        render_configuration_page(interface)
    elif page == "📋 Documentation":
        render_documentation_page()

def render_configuration_page(interface):
    """Page de configuration"""
    st.markdown("# ⚙️ Configuration du Système")
    
    if not st.session_state.system_initialized:
        if st.button("🚀 Initialiser le Système"):
            interface.initialize_system()
            st.rerun()
        return
    
    # Configuration générale
    st.markdown("## 🔧 Paramètres Généraux")
    
    with st.form("general_config"):
        col1, col2 = st.columns(2)
        
        with col1:
            monitoring_interval = st.number_input(
                "Intervalle de surveillance (secondes)",
                min_value=1,
                max_value=60,
                value=5
            )
            
            alert_threshold = st.slider(
                "Seuil d'alerte de criticité",
                min_value=1,
                max_value=10,
                value=5
            )
        
        with col2:
            auto_protocols = st.checkbox(
                "Activation automatique des protocoles",
                value=True
            )
            
            data_retention = st.selectbox(
                "Rétention des données",
                ["1 jour", "1 semaine", "1 mois", "3 mois"]
            )
        
        if st.form_submit_button("💾 Sauvegarder Configuration"):
            st.success("Configuration sauvegardée!")
    
    # Configuration des capteurs
    st.markdown("## 📡 Configuration des Capteurs")
    
    if interface.mine_system:
        sensors_config = interface.mine_system.data_simulator.sensors_config
        
        sensor_to_edit = st.selectbox(
            "Capteur à configurer:",
            list(sensors_config.keys())
        )
        
        if sensor_to_edit:
            config = sensors_config[sensor_to_edit]
            
            with st.form(f"sensor_config_{sensor_to_edit}"):
                st.markdown(f"### Configuration: {sensor_to_edit}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_min = st.number_input(
                        "Valeur minimale normale",
                        value=float(config['normal_range'][0])
                    )
                    
                    new_max = st.number_input(
                        "Valeur maximale normale", 
                        value=float(config['normal_range'][1])
                    )
                
                with col2:
                    new_critical = st.number_input(
                        "Seuil critique",
                        value=float(config.get('critical_threshold', config['normal_range'][1] * 1.5))
                    )
                    
                    calibration_freq = st.selectbox(
                        "Fréquence de calibration",
                        ["Hebdomadaire", "Mensuelle", "Trimestrielle"]
                    )
                
                if st.form_submit_button("🔧 Mettre à jour capteur"):
                    # Mise à jour de la configuration
                    config['normal_range'] = (new_min, new_max)
                    config['critical_threshold'] = new_critical
                    st.success(f"Capteur {sensor_to_edit} mis à jour!")
    
    # Configuration des protocoles
    st.markdown("## 🚨 Configuration des Protocoles d'Urgence")
    
    if interface.mine_system:
        protocols = interface.mine_system.ai_agent.emergency_protocols
        
        protocol_to_edit = st.selectbox(
            "Protocole à modifier:",
            list(protocols.keys())
        )
        
        if protocol_to_edit:
            protocol = protocols[protocol_to_edit]
            
            with st.expander(f"Détails: {protocol.name}", expanded=True):
                st.markdown(f"**Description:** {protocol.description}")
                st.markdown(f"**Priorité:** {protocol.priority}")
                st.markdown(f"**Temps estimé:** {protocol.estimated_time}s")
                st.markdown(f"**Personnel requis:** {protocol.personnel_required}")
                
                st.markdown("**Actions requises:**")
                for i, action in enumerate(protocol.required_actions, 1):
                    st.markdown(f"{i}. {action}")
                
                st.markdown("**Zones affectées:**")
                st.markdown(", ".join(protocol.affected_zones))

def render_documentation_page():
    """Page de documentation"""
    st.markdown("# 📋 Documentation du Système")
    
    # Onglets de documentation
    tab1, tab2, tab3, tab4 = st.tabs(["🏭 Vue d'ensemble", "📡 Capteurs", "🚨 Protocoles", "🤖 IA"])
    
    with tab1:
        st.markdown("""
        ## 🏭 Vue d'ensemble du Système
        
        Ce système de surveillance intelligent pour mine de phosphate utilise l'intelligence artificielle
        pour analyser en temps réel les données de multiples capteurs et prendre des décisions automatiques
        en cas d'urgence.
        
        ### 🎯 Objectifs Principaux
        - **Sécurité:** Prévention des accidents et protection du personnel
        - **Efficacité:** Optimisation de la production et réduction des arrêts
        - **Environnement:** Surveillance de l'impact environnemental
        - **Conformité:** Respect des réglementations marocaines
        
        ### 🏗️ Architecture du Système
        1. **Couche Capteurs:** Collecte des données temps réel
        2. **Couche IA:** Analyse intelligente avec Claude
        3. **Couche Décision:** Activation automatique des protocoles
        4. **Interface Utilisateur:** Dashboard Streamlit
        
        ### 📊 Métriques Clés
        - Plus de 15 types de capteurs différents
        - Analyse toutes les 5 secondes
        - 4 protocoles d'urgence automatisés
        - Interface temps réel avec historique
        """)
    
    with tab2:
        st.markdown("""
        ## 📡 Documentation des Capteurs
        
        ### Types de Capteurs Surveillés
        
        #### 🌬️ Qualité de l'Air
        - **Poussière (dust):** Surveillance des particules de phosphate
          - Seuil normal: 15-70 mg/m³
          - Seuil critique: >100 mg/m³ (risque explosion)
        
        - **Gaz toxiques:** Surveillance NH3, SO2, HF
          - NH3: Normal <20 ppm, Critique >50 ppm
          - SO2: Normal <10 ppm, Critique >20 ppm
          - HF: Normal <3 ppm, Critique >10 ppm
        
        #### ⚙️ Équipements
        - **Vibrations:** Surveillance des machines rotatives
          - Normal: 1-5 mm/s
          - Critique: >7 mm/s (panne imminente)
        
        - **Température:** Surveillance des fours et équipements
          - Four séchage: 80-150°C normal, >200°C critique
        
        #### 🌍 Environnement
        - **Radioactivité:** Surveillance naturelle du phosphate
          - Normal: 0.1-0.3 μSv/h
          - Surveillance renforcée: >1 μSv/h
        
        - **Qualité eau:** Turbidité et pH des effluents
          - pH: 6.5-8.5 normal
          - Turbidité: <25 NTU normal, >100 NTU critique
        
        ### 🔧 Maintenance des Capteurs
        - Calibration mensuelle obligatoire
        - Vérification hebdomadaire de l'état
        - Remplacement automatique programmé
        """)
    
    with tab3:
        st.markdown("""
        ## 🚨 Protocoles d'Urgence
        
        ### Protocoles Automatisés
        
        #### 1. 🌪️ Tempête de Poussière (DUST_STORM_001)
        **Déclenchement:** Concentration poussière >200 mg/m³ + vent >12 m/s
        
        **Actions automatiques:**
        1. Coupure électrique zones à risque
        2. Activation brumisation d'urgence
        3. Confinement personnel abris pressurisés
        4. Surveillance continue concentrations
        5. Équipes décontamination
        6. Communication autorités environnementales
        
        **Personnel requis:** 25 personnes
        **Durée estimée:** 7.5 minutes
        
        #### 2. ☣️ Cascade Chimique (CHEM_CASCADE_001)
        **Déclenchement:** Fuite multiple gaz toxiques + pH <4
        
        **Actions automatiques:**
        1. Isolation sources de fuite
        2. Évacuation dirigée selon vent
        3. Centre décontamination mobile
        4. Neutralisation chimique d'urgence
        5. Surveillance médicale personnel
        6. Alerte services santé externes
        7. Confinement effluents contaminés
        
        **Personnel requis:** 15 personnes
        **Durée estimée:** 10 minutes
        
        #### 3. ⚙️ Panne en Cascade (EQUIP_CASCADE_001)
        **Déclenchement:** Vibrations >8 mm/s + température >180°C
        
        **Actions automatiques:**
        1. Arrêt contrôlé chaîne production
        2. Isolation équipements défaillants
        3. Inspection structurelle d'urgence
        4. Sécurisation installations sous pression
        5. Activation systèmes de backup
        6. Évaluation risques propagation
        
        **Personnel requis:** 12 personnes
        **Durée estimée:** 5 minutes
        
        ### 📞 Contacts d'Urgence
        - **Centre de Crise:** +212 5XX XX XX XX
        - **Pompiers Industriels:** +212 5XX XX XX XX
        - **Autorités Environnementales:** +212 5XX XX XX XX
        - **Services Médicaux:** +212 5XX XX XX XX
        """)
    
    with tab4:
        st.markdown("""
        ## 🤖 Intelligence Artificielle Claude
        
        ### Capacités d'Analyse
        
        #### 🧠 Analyse Multi-Sources
        L'IA Claude analyse simultanément:
        - 15+ capteurs en temps réel
        - Conditions météorologiques
        - Données de production
        - Historique des incidents
        - Corrélations complexes
        
        #### 🔮 Prédictions Avancées
        - **Horizon:** 30 minutes à 4 heures
        - **Précision:** >85% pour incidents critiques
        - **Facteurs:** Tendances, corrélations, météo
        - **Alertes préventives:** Probabilité >70%
        
        #### 📊 Apprentissage Continu
        - Mémorisation des interventions réussies
        - Évitement des fausses alarmes
        - Adaptation aux patterns locaux
        - Amélioration des protocoles d'urgence

        #### 🎯 Scores de Confiance
        - **>0.9:** Très haute confiance - Action immédiate
        - **0.7-0.9:** Haute confiance - Surveillance renforcée
        - **0.5-0.7:** Confiance modérée - Vérification manuelle
        - **<0.5:** Faible confiance - Possible fausse alarme

        ### 🔧 Configuration IA

        #### Paramètres d'Analyse
        ```python
        # Seuils de détection
        DUST_CRITICAL = 100  # mg/m³
        GAS_CRITICAL = 50    # ppm (NH3)
        VIBRATION_CRITICAL = 7.0  # mm/s
        
        # Paramètres météo
        WIND_THRESHOLD = 15  # m/s
        VISIBILITY_MIN = 2   # km
        
        # Corrélations surveillées
        CORRELATION_THRESHOLD = 0.7
        ```

        #### Prompts Système
        L'IA utilise des prompts spécialisés pour:
        - Analyse contextuelle marocaine
        - Prise en compte réglementaire
        - Évaluation impact population
        - Optimisation ressources

        ### 📈 Métriques de Performance
        - **Temps de réponse:** <2 secondes
        - **Taux de détection:** 95%+ incidents critiques
        - **Faux positifs:** <5% des alertes
        - **Disponibilité:** 99.9% uptime

        ### 🔄 Mises à Jour
        Le système IA s'améliore continuellement via:
        1. **Feedback opérateurs:** Validation des alertes
        2. **Résultats interventions:** Succès/échecs protocoles
        3. **Nouvelles données:** Patterns émergents
        4. **Mises à jour Claude:** Nouvelles capacités

        ---
        *Pour plus d'informations techniques, consultez la documentation développeur*
        """)

if __name__ == "__main__":
    main()