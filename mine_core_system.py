import asyncio
import json
import random
import time
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import anthropic
from dataclasses import dataclass, asdict
import logging
from enum import Enum
import threading
from collections import deque
import math

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class SensorStatus(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    location: str
    zone: str
    timestamp: datetime
    status: SensorStatus
    calibration_date: datetime
    maintenance_due: bool = False
    
    def to_dict(self):
        return {
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'value': self.value,
            'unit': self.unit,
            'location': self.location,
            'zone': self.zone,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'calibration_date': self.calibration_date.isoformat(),
            'maintenance_due': self.maintenance_due
        }

@dataclass
class WeatherCondition:
    temperature: float  # °C
    humidity: float     # %
    wind_speed: float   # m/s
    wind_direction: float  # degrees
    pressure: float     # hPa
    visibility: float   # km
    precipitation: float  # mm/h
    
    def to_dict(self):
        return {
            'temperature': self.temperature,
            'humidity': self.humidity,
            'wind_speed': self.wind_speed,
            'wind_direction': self.wind_direction,
            'pressure': self.pressure,
            'visibility': self.visibility,
            'precipitation': self.precipitation
        }

@dataclass
class ProductionMetrics:
    hourly_production: float  # tonnes/heure
    quality_grade: float      # % P2O5
    energy_consumption: float # kWh
    water_usage: float        # m³/h
    waste_generated: float    # tonnes/h
    efficiency_rate: float    # %
    
    def to_dict(self):
        return {
            'hourly_production': self.hourly_production,
            'quality_grade': self.quality_grade,
            'energy_consumption': self.energy_consumption,
            'water_usage': self.water_usage,
            'waste_generated': self.waste_generated,
            'efficiency_rate': self.efficiency_rate
        }

@dataclass
class PersonnelData:
    zone: str
    personnel_count: int
    shift_supervisor: str
    emergency_trained: int
    last_safety_drill: datetime

    def to_dict(self):
        return {
            'zone': self.zone,
            'personnel_count': self.personnel_count,
            'shift_supervisor': self.shift_supervisor,
            'emergency_trained': self.emergency_trained,
            'last_safety_drill': self.last_safety_drill.isoformat()
        }

@dataclass
class EmergencyProtocol:
    protocol_id: str
    name: str
    description: str
    priority: int
    estimated_time: int
    required_actions: List[str]
    affected_zones: List[str]
    personnel_required: int
    equipment_needed: List[str]

class DatabaseManager:
    """Gestionnaire de base de données pour l'historique"""
    
    def __init__(self, db_path: str = "mine_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des lectures capteurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                sensor_type TEXT,
                value REAL,
                unit TEXT,
                location TEXT,
                zone TEXT,
                timestamp TEXT,
                status TEXT
            )
        ''')
        
        # Table des analyses IA
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                risk_level TEXT,
                anomalies TEXT,
                affected_zones TEXT,
                confidence_score REAL,
                reasoning TEXT
            )
        ''')
        
        # Table des protocoles exécutés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executed_protocols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol_id TEXT,
                start_time TEXT,
                end_time TEXT,
                success BOOLEAN,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_sensor_reading(self, reading: SensorReading):
        """Sauvegarde une lecture de capteur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_readings 
            (sensor_id, sensor_type, value, unit, location, zone, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            reading.sensor_id, reading.sensor_type, reading.value,
            reading.unit, reading.location, reading.zone,
            reading.timestamp.isoformat(), reading.status.value
        ))
        
        conn.commit()
        conn.close()
    
    def get_sensor_history(self, sensor_id: str, hours: int = 24) -> List[Dict]:
        """Récupère l'historique d'un capteur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        cursor.execute('''
            SELECT * FROM sensor_readings 
            WHERE sensor_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        ''', (sensor_id, since.isoformat()))
        
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return result

class AdvancedPhosphateMineSimulator:
    """Simulateur avancé de mine de phosphate"""
    
    def __init__(self):
        self.weather = WeatherCondition(25, 65, 3.2, 180, 1013, 10, 0)
        self.production = ProductionMetrics(150, 28.5, 2400, 45, 12, 0.85)
        
        # Configuration avancée des capteurs
        self.sensors_config = {
            # Zone 1
            "dust_extr_01": {"type": "dust", "zone": "Zone 1", "location": "Fosse_Nord", 
                           "normal_range": (15, 45), "unit": "mg/m³", "critical_threshold": 100},
            "dust_extr_02": {"type": "dust", "zone": "Zone 1", "location": "Fosse_Sud", 
                           "normal_range": (20, 50), "unit": "mg/m³", "critical_threshold": 100},
            
            # Zone 2
            "dust_trait_01": {"type": "dust", "zone": "Zone 2", "location": "Broyeur_Primaire", 
                            "normal_range": (30, 70), "unit": "mg/m³", "critical_threshold": 120},
            "dust_trait_02": {"type": "dust", "zone": "Zone 2", "location": "Broyeur_Secondaire", 
                            "normal_range": (25, 65), "unit": "mg/m³", "critical_threshold": 120},
            "vibration_br_01": {"type": "vibration", "zone": "Zone 2", "location": "Broyeur_Boulets", 
                               "normal_range": (1.5, 4.5), "unit": "mm/s", "critical_threshold": 7.0},
            "vibration_br_02": {"type": "vibration", "zone": "Zone 2", "location": "Concasseur", 
                               "normal_range": (1.0, 3.5), "unit": "mm/s", "critical_threshold": 6.0},
            
            # Zone 3
            "gas_nh3_01": {"type": "ammonia", "zone": "Zone 3", "location": "Réacteur_1", 
                          "normal_range": (2, 15), "unit": "ppm", "critical_threshold": 50},
            "gas_so2_01": {"type": "sulfur_dioxide", "zone": "Zone 3", "location": "Acidulation", 
                          "normal_range": (1, 8), "unit": "ppm", "critical_threshold": 20},
            "gas_hf_01": {"type": "hydrogen_fluoride", "zone": "Zone 3", "location": "Attaque_Acide", 
                         "normal_range": (0.5, 3), "unit": "ppm", "critical_threshold": 10},
            "ph_bassin_01": {"type": "ph", "zone": "Zone 3", "location": "Bassin_Neutralisation", 
                           "normal_range": (6.5, 8.5), "unit": "pH", "critical_threshold": 5.0},
            
            # Zone 4
            "temp_four_01": {"type": "temperature", "zone": "Zone 4", "location": "Four_Séchage", 
                           "normal_range": (80, 150), "unit": "°C", "critical_threshold": 200},
            "pressure_pipe_01": {"type": "pressure", "zone": "Zone 4", "location": "Pipeline_Principal", 
                               "normal_range": (2.5, 5.5), "unit": "bar", "critical_threshold": 8.0},
            "level_bassin_01": {"type": "level", "zone": "Zone 4", "location": "Bassin_Décantation", 
                              "normal_range": (3.0, 7.5), "unit": "m", "critical_threshold": 9.0},
            
            # Zone 5
            "air_quality_01": {"type": "air_quality", "zone": "Zone 5", "location": "Station_Météo", 
                             "normal_range": (50, 150), "unit": "AQI", "critical_threshold": 300},
            
            # Zone 6
            "radiation_01": {"type": "radiation", "zone": "Zone 6", "location": "Zone_Stockage", 
                           "normal_range": (0.1, 0.3), "unit": "μSv/h", "critical_threshold": 1.0},
            
            # Eau et environnement
            "water_flow_01": {"type": "flow", "zone": "Zone 6", "location": "Circuit_Eau", 
                            "normal_range": (150, 300), "unit": "m³/h", "critical_threshold": 50},
            "turbidity_01": {"type": "turbidity", "zone": "environnement", "location": "Effluent_Sortie", 
                           "normal_range": (5, 25), "unit": "NTU", "critical_threshold": 100}
        }
        
        # Personnel par zone
        self.personnel_data = {
            "Zone 1": PersonnelData("Zone 1", 12, "Superviseur 1", 8, datetime.now() - timedelta(days=15)),
            "Zone 2": PersonnelData("Zone 2", 18, "Superviseur 2", 14, datetime.now() - timedelta(days=8)),
            "Zone 3": PersonnelData("Zone 3", 8, "Superviseur 3", 8, datetime.now() - timedelta(days=3)),
            "Zone 4": PersonnelData("Zone 4", 6, "Superviseur 4", 4, datetime.now() - timedelta(days=12)),
            "Zone 5": PersonnelData("Zone 5", 4, "Superviseur 5", 3, datetime.now() - timedelta(days=20)),
            "Zone 6": PersonnelData("Zone 6", 3, "Superviseur 6", 3, datetime.now() - timedelta(days=5))
        }
        
        # État des anomalies
        self.active_anomalies = {}
        self.sensor_history = {sensor_id: deque(maxlen=100) for sensor_id in self.sensors_config.keys()}
        
        # Simulation de cycles de production
        self.production_cycle = 0
        self.maintenance_schedule = {}
        
    def update_weather(self):
        """Met à jour les conditions météorologiques"""
        # Simulation réaliste basée sur le climat marocain
        base_temp = 25 + 10 * math.sin(time.time() / 86400 * 2 * math.pi)  # Cycle journalier
        self.weather.temperature = base_temp + random.uniform(-5, 5)
        self.weather.humidity = max(20, min(95, 65 + random.uniform(-20, 20)))
        self.weather.wind_speed = max(0, 3.2 + random.uniform(-2, 4))
        self.weather.pressure = 1013 + random.uniform(-10, 10)
        
        # Impact météo sur la poussière
        dust_factor = 1.0
        if self.weather.wind_speed > 8:
            dust_factor = 1.5  # Plus de poussière avec vent fort
        if self.weather.humidity < 30:
            dust_factor *= 1.3  # Air sec = plus de poussière
            
        return dust_factor
    
    def calculate_production_impact(self) -> float:
        """Calcule l'impact sur la production"""
        impact_factor = 1.0
        
        # Impact des anomalies
        for anomaly in self.active_anomalies.values():
            if anomaly['severity'] == 'critical':
                impact_factor *= 0.7  # Réduction de 30%
            elif anomaly['severity'] == 'warning':
                impact_factor *= 0.9   # Réduction de 10%
        
        # Impact météorologique
        if self.weather.wind_speed > 12:
            impact_factor *= 0.8  # Arrêt partiel par vent fort
        
        if self.weather.visibility < 2:
            impact_factor *= 0.6  # Visibilité réduite
            
        self.production.hourly_production = 150 * impact_factor
        self.production.efficiency_rate = min(1.0, impact_factor * 0.85)
        
        return impact_factor
    
    def generate_realistic_reading(self, sensor_id: str) -> SensorReading:
        """Génère une lecture réaliste de capteur"""
        config = self.sensors_config[sensor_id]
        min_val, max_val = config["normal_range"]
        
        # Facteurs d'influence
        weather_factor = self.update_weather() if config["type"] == "dust" else 1.0
        production_factor = self.production.efficiency_rate
        
        # Pattern temporel (cycles de production)
        time_factor = 1 + 0.2 * math.sin(time.time() / 3600 * 2 * math.pi)
        
        # Valeur de base avec tendance
        if sensor_id in self.sensor_history and self.sensor_history[sensor_id]:
            last_value = self.sensor_history[sensor_id][-1].value
            trend = random.uniform(-0.1, 0.1) * last_value
        else:
            trend = 0
            
        base_value = random.uniform(min_val, max_val)
        
        # Application des facteurs
        if config["type"] == "dust":
            value = base_value * weather_factor * time_factor + trend
        elif config["type"] in ["vibration", "noise"]:
            value = base_value * production_factor * time_factor + trend
        elif config["type"] == "temperature":
            value = base_value + self.weather.temperature * 0.1 + trend
        else:
            value = base_value * time_factor + trend
            
        value = max(0, value)
        
        # Détermination du statut
        status = SensorStatus.NORMAL
        critical_threshold = config.get("critical_threshold", max_val * 1.5)
        warning_threshold = max_val * 0.85
        
        if value >= critical_threshold:
            status = SensorStatus.CRITICAL
        elif value >= warning_threshold:
            status = SensorStatus.WARNING
        
        # Simulation de pannes capteurs (rare)
        if random.random() < 0.001:  # 0.1% de chance
            status = SensorStatus.OFFLINE
            value = 0
        
        reading = SensorReading(
            sensor_id=sensor_id,
            sensor_type=config["type"],
            value=round(value, 2),
            unit=config["unit"],
            location=config["location"],
            zone=config["zone"],
            timestamp=datetime.now(),
            status=status,
            calibration_date=datetime.now() - timedelta(days=random.randint(1, 90)),
            maintenance_due=random.random() < 0.05  # 5% chance maintenance due
        )
        
        # Ajouter à l'historique
        self.sensor_history[sensor_id].append(reading)
        
        return reading
    
    def simulate_complex_anomaly(self, anomaly_type: str) -> Dict[str, SensorReading]:
        """Simule des anomalies complexes et interconnectées"""
        readings = {}
        
        if anomaly_type == "dust_storm_impact":
            # Tempête de poussière affectant plusieurs zones
            affected_sensors = [s for s, c in self.sensors_config.items() if c["type"] == "dust"]
            for sensor_id in affected_sensors:
                config = self.sensors_config[sensor_id]
                anomaly_value = random.uniform(200, 400)  # Très critique
                readings[sensor_id] = SensorReading(
                    sensor_id=sensor_id,
                    sensor_type=config["type"],
                    value=anomaly_value,
                    unit=config["unit"],
                    location=config["location"],
                    zone=config["zone"],
                    timestamp=datetime.now(),
                    status=SensorStatus.CRITICAL,
                    calibration_date=datetime.now() - timedelta(days=30),
                    maintenance_due=False
                )
            
            # Impact sur la visibilité
            readings["air_quality_01"] = self.generate_realistic_reading("air_quality_01")
            readings["air_quality_01"].value = 350  # AQI dangereux
            readings["air_quality_01"].status = SensorStatus.CRITICAL
            
        elif anomaly_type == "chemical_leak_cascade":
            # Fuite chimique avec effet en cascade
            primary_sensors = ["gas_nh3_01", "gas_so2_01", "gas_hf_01"]
            for sensor_id in primary_sensors:
                config = self.sensors_config[sensor_id]
                readings[sensor_id] = SensorReading(
                    sensor_id=sensor_id,
                    sensor_type=config["type"],
                    value=config["critical_threshold"] * random.uniform(1.5, 3.0),
                    unit=config["unit"],
                    location=config["location"],
                    zone=config["zone"],
                    timestamp=datetime.now(),
                    status=SensorStatus.CRITICAL,
                    calibration_date=datetime.now() - timedelta(days=15),
                    maintenance_due=True
                )
            
            # pH affecté
            readings["ph_bassin_01"] = self.generate_realistic_reading("ph_bassin_01")
            readings["ph_bassin_01"].value = 3.2  # Très acide
            readings["ph_bassin_01"].status = SensorStatus.CRITICAL
            
        elif anomaly_type == "equipment_failure_chain":
            # Panne en chaîne des équipements
            primary_equipment = ["vibration_br_01", "vibration_br_02", "temp_four_01"]
            for sensor_id in primary_equipment:
                config = self.sensors_config[sensor_id]
                readings[sensor_id] = SensorReading(
                    sensor_id=sensor_id,
                    sensor_type=config["type"],
                    value=config["critical_threshold"] * random.uniform(1.2, 2.0),
                    unit=config["unit"],
                    location=config["location"],
                    zone=config["zone"],
                    timestamp=datetime.now(),
                    status=SensorStatus.CRITICAL,
                    calibration_date=datetime.now() - timedelta(days=45),
                    maintenance_due=True
                )
            
            # Impact sur la pression et le débit
            readings["pressure_pipe_01"] = self.generate_realistic_reading("pressure_pipe_01")
            readings["pressure_pipe_01"].value = 0.8  # Pression très basse
            readings["pressure_pipe_01"].status = SensorStatus.CRITICAL
            
        # Compléter avec des lectures normales pour les autres capteurs
        for sensor_id in self.sensors_config.keys():
            if sensor_id not in readings:
                readings[sensor_id] = self.generate_realistic_reading(sensor_id)
                
        return readings
    
    def get_all_sensor_readings(self) -> Dict[str, SensorReading]:
        """Obtient toutes les lectures de capteurs de manière optimisée"""
        readings = {}
        weather_factor = self.update_weather()  # Calcul unique du facteur météo
        production_factor = self.calculate_production_impact()  # Calcul unique de l'impact production
        
        # Génération en lot des lectures
        for sensor_id, config in self.sensors_config.items():
            if sensor_id in self.active_anomalies:
                readings[sensor_id] = self._generate_anomaly_reading(sensor_id)
            else:
                readings[sensor_id] = self._generate_optimized_reading(
                    sensor_id, config, weather_factor, production_factor
                )
        
        return readings

    def _generate_optimized_reading(self, sensor_id: str, config: dict, 
                                  weather_factor: float, production_factor: float) -> SensorReading:
        """Génère une lecture optimisée de capteur"""
        min_val, max_val = config["normal_range"]
        
        # Utilisation des facteurs pré-calculés
        time_factor = 1 + 0.2 * math.sin(time.time() / 3600 * 2 * math.pi)
        
        # Calcul optimisé de la valeur
        if config["type"] == "dust":
            base_value = random.uniform(min_val, max_val)
            value = base_value * weather_factor * time_factor
        elif config["type"] in ["vibration", "noise"]:
            base_value = random.uniform(min_val, max_val)
            value = base_value * production_factor * time_factor
        else:
            value = random.uniform(min_val, max_val) * time_factor
        
        value = max(0, value)
        
        # Détermination rapide du statut
        status = SensorStatus.NORMAL
        if value >= config.get("critical_threshold", max_val * 1.5):
            status = SensorStatus.CRITICAL
        elif value >= max_val * 0.85:
            status = SensorStatus.WARNING
        
        return SensorReading(
            sensor_id=sensor_id,
            sensor_type=config["type"],
            value=round(value, 2),
            unit=config["unit"],
            location=config["location"],
            zone=config["zone"],
            timestamp=datetime.now(),
            status=status,
            calibration_date=datetime.now() - timedelta(days=30),
            maintenance_due=False
        )

    # ...existing code...
    
    def trigger_anomaly(self, anomaly_type: str, duration: int = 5, severity: str = "critical"):
        """Déclenche une anomalie complexe"""
        anomaly_id = f"{anomaly_type}_{int(time.time())}"
        self.active_anomalies[anomaly_id] = {
            'type': anomaly_type,
            'duration': duration,
            'severity': severity,
            'start_time': datetime.now()
        }
        logger.info(f"Anomalie complexe déclenchée: {anomaly_type} (durée: {duration} cycles)")
    
    def get_zone_status(self) -> Dict[str, Dict]:
        """Retourne le statut de chaque zone"""
        zone_status = {}
        
        for zone_name, personnel in self.personnel_data.items():
            # Compter les capteurs par statut dans chaque zone
            zone_sensors = [s for s, c in self.sensors_config.items() if c["zone"] == zone_name]
            
            status_count = {"normal": 0, "warning": 0, "critical": 0, "offline": 0}
            
            # Simuler les statuts actuels (en réalité, on utiliserait les dernières lectures)
            for sensor_id in zone_sensors:
                reading = self.generate_realistic_reading(sensor_id)
                status_count[reading.status.value] += 1
            
            # Déterminer le statut global de la zone
            overall_status = "normal"
            if status_count["critical"] > 0:
                overall_status = "critical"
            elif status_count["warning"] > 0:
                overall_status = "warning"
            elif status_count["offline"] > 0:
                overall_status = "degraded"
            
            zone_status[zone_name] = {
                "status": overall_status,
                "personnel": personnel.to_dict(),  # Use to_dict() method
                "sensor_count": len(zone_sensors),
                "sensor_status": status_count,
                "active_anomalies": len([a for a in self.active_anomalies.values() 
                                       if any(self.sensors_config[s]["zone"] == zone_name 
                                            for s in self.sensors_config.keys())])
            }
        
        return zone_status

class EnhancedClaudeAgent:
    """Agent IA Claude amélioré pour la gestion d'urgence"""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Protocoles d'urgence étendus
        self.emergency_protocols = {
            "dust_storm_emergency": EmergencyProtocol(
                protocol_id="DUST_STORM_001",
                name="Protocole Tempête de Poussière",
                description="Intervention d'urgence pour tempête de poussière avec risque explosion",
                priority=1,
                estimated_time=450,
                required_actions=[
                    "Arrêt immédiat de tous les équipements électriques non-essentiels",
                    "Activation du système de brumisation d'urgence",
                    "Confinement du personnel dans les abris pressurisés",
                    "Surveillance continue des concentrations de poussière",
                    "Activation des équipes de décontamination",
                    "Communication avec les autorités environnementales"
                ],
                affected_zones=["extraction", "traitement", "stockage"],
                personnel_required=25,
                equipment_needed=["Systèmes de brumisation", "Respirateurs P3", "Détecteurs portables"]
            ),
            
            "chemical_cascade_emergency": EmergencyProtocol(
                protocol_id="CHEM_CASCADE_001", 
                name="Protocole Cascade Chimique",
                description="Intervention pour fuite chimique avec effet domino",
                priority=1,
                estimated_time=600,
                required_actions=[
                    "Isolation immédiate des sources de fuite",
                    "Évacuation dirigée selon la rose des vents",
                    "Activation du centre de décontamination mobile",
                    "Neutralisation chimique d'urgence",
                    "Surveillance médicale du personnel exposé",
                    "Alerte aux services de santé externes",
                    "Confinement des effluents contaminés"
                ],
                affected_zones=["chimique", "traitement", "environnement"],
                personnel_required=15,
                equipment_needed=["Combinaisons étanches", "Neutralisants chimiques", "Ambulance"]
            ),
            
            "equipment_cascade_failure": EmergencyProtocol(
                protocol_id="EQUIP_CASCADE_001",
                name="Protocole Panne en Cascade",
                description="Intervention pour pannes d'équipements en chaîne",
                priority=2,
                estimated_time=300,
                required_actions=[
                    "Arrêt contrôlé de la chaîne de production",
                    "Isolation des équipements défaillants",
                    "Inspection structurelle d'urgence",
                    "Mise en sécurité des installations sous pression",
                    "Activation des systèmes de backup",
                    "Évaluation des risques de propagation"
                ],
                affected_zones=["traitement", "transport"],
                personnel_required=12,
                equipment_needed=["Outils de diagnostic", "Équipements de levage", "Pièces de rechange"]
            ),
            
            "environmental_contamination": EmergencyProtocol(
                protocol_id="ENV_CONTAM_001",
                name="Protocole Contamination Environnementale", 
                description="Intervention pour contamination de l'environnement",
                priority=2,
                estimated_time=720,
                required_actions=[
                    "Arrêt des rejets à la source",
                    "Confinement de la zone contaminée", 
                    "Prélèvements d'urgence eau/sol/air",
                    "Notification aux autorités environnementales",
                    "Activation du plan de dépollution",
                    "Surveillance sanitaire de la population locale"
                ],
                affected_zones=["environnement", "chimique"],
                personnel_required=8,
                equipment_needed=["Kits de prélèvement", "Barrières étanches", "Laboratoire mobile"]
            )
        }
        
        self.context_memory = deque(maxlen=20)  # Mémoire étendue
        self.active_protocols = []
        self.learning_data = {"successful_interventions": [], "false_alarms": []}
    
    async def analyze_comprehensive_data(self, sensor_readings: Dict[str, SensorReading], 
                                       weather: WeatherCondition, production: ProductionMetrics,
                                       zone_status: Dict[str, Dict]) -> Dict[str, Any]:
        """Analyse complète avec contexte étendu"""
        
        # Préparer les données contextuelles
        sensor_data_text = self._format_comprehensive_data(sensor_readings, weather, production, zone_status)
        
        prompt = f"""
Tu es un agent IA expert en sécurité industrielle pour une mine de phosphate au Maroc. 
Tu as accès à des données en temps réel et à un historique d'analyses.

DONNÉES ACTUELLES COMPLÈTES:
{sensor_data_text}

CONTEXTE HISTORIQUE:
{self._get_enhanced_context()}

APPRENTISSAGE CONTINU:
- Interventions réussies: {len(self.learning_data['successful_interventions'])}
- Fausses alarmes évitées: {len(self.learning_data['false_alarms'])}

MISSION AVANCÉE:
1. Analyser l'ensemble des données multi-sources
2. Identifier les corrélations et tendances dangereuses
3. Prédire les risques émergents (prochaines 2-4 heures)
4. Évaluer l'impact multi-zones
5. Recommander les actions graduées selon la criticité

SPÉCIFICITÉS TECHNIQUES MAROC:
- Phosphate naturellement radioactif (uranium, thorium)
- Climat semi-aride: tempêtes de sable fréquentes
- Réglementation marocaine: Décret 2-12-85 (seuils poussière)
- Population locale: villages à 5km (Khouribga/Youssoufia)

SEUILS CRITIQUES CONTEXTUELS:
- Poussière P2O5: >100mg/m³ = explosion risk, >200mg/m³ = évacuation
- Gaz NH3: >50ppm critique, >100ppm évacuation
- HF: >3ppm alerte, >10ppm masques obligatoires
- Radioactivité: >1μSv/h = surveillance renforcée
- Conditions météo: vent >15m/s = arrêt extraction

ANALYSE MULTICRITÈRES REQUISE:
- Corrélations temporelles (tendances 30min)
- Impacts météorologiques (direction vent = dispersion)
- Charge de travail actuelle vs capacité
- État de maintenance préventive
- Proximité population civile

RÉPONSE JSON STRUCTURÉE:
{{
    "risk_assessment": {{
        "current_level": "NORMAL/WARNING/CRITICAL/EMERGENCY",
        "predicted_level_2h": "NORMAL/WARNING/CRITICAL/EMERGENCY", 
        "confidence_score": 0.0-1.0,
        "primary_risks": ["liste des risques principaux"],
        "secondary_risks": ["risques secondaires/cascade"]
    }},
    "zone_analysis": {{
        "affected_zones": ["zones avec problèmes"],
        "safe_zones": ["zones sûres pour évacuation"],
        "personnel_at_risk": {{
            "immediate": number,
            "potential": number,
            "evacuation_routes": ["routes recommandées"]
        }}
    }},
    "correlations_detected": [
        {{
            "type": "météo/équipement/chimique",
            "description": "relation identifiée",
            "risk_amplification": "facteur multiplicateur"
        }}
    ],
    "immediate_actions": [
        {{
            "priority": 1-5,
            "action": "action spécifique",
            "zone": "zone concernée",
            "estimated_time": "durée en minutes",
            "personnel_needed": number
        }}
    ],
    "predictive_alerts": [
        {{
            "timeframe": "30min/1h/2h",
            "probability": 0.0-1.0,
            "scenario": "description du scénario",
            "preventive_measures": ["mesures préventives"]
        }}
    ],
    "protocol_recommendation": {{
        "protocol_needed": "ID protocole ou null",
        "modifications": ["adaptations contextuelles"],
        "resource_requirements": {{
            "personnel": number,
            "equipment": ["équipements spécifiques"],
            "external_support": boolean
        }}
    }},
    "learning_feedback": {{
        "pattern_recognition": "nouveaux patterns détectés",
        "historical_comparison": "comparaison situations similaires",
        "improvement_suggestions": ["suggestions d'amélioration"]
    }},
    "detailed_reasoning": "analyse détaillée multi-paragraphes"
}}
"""

        try:
            response = await self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parser la réponse JSON
            analysis = json.loads(response.content[0].text)
            
            # Enrichir avec des métadonnées
            analysis["analysis_timestamp"] = datetime.now().isoformat()
            analysis["data_quality_score"] = self._calculate_data_quality(sensor_readings)
            analysis["environmental_factors"] = self._assess_environmental_impact(weather)
            
            # Ajouter au contexte mémoire
            self.context_memory.append({
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "sensor_summary": self._create_sensor_summary(sensor_readings),
                "weather_snapshot": asdict(weather),
                "production_snapshot": asdict(production)
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur analyse Claude complète: {e}")
            return {
                "risk_assessment": {"current_level": "UNKNOWN", "confidence_score": 0.0},
                "error": str(e)
            }
    
    def _format_comprehensive_data(self, readings: Dict[str, SensorReading], 
                                 weather: WeatherCondition, production: ProductionMetrics,
                                 zone_status: Dict[str, Dict]) -> str:
        """Formate toutes les données pour l'analyse"""
        
        # Données capteurs par zone
        zones_data = {}
        for sensor_id, reading in readings.items():
            zone = reading.zone
            if zone not in zones_data:
                zones_data[zone] = []
            zones_data[zone].append(f"  - {sensor_id}: {reading.value} {reading.unit} [{reading.status.value}] @ {reading.location}")
        
        formatted_zones = []
        for zone, sensors in zones_data.items():
            zone_info = zone_status.get(zone, {})
            personnel_count = zone_info.get('personnel', {}).get('personnel_count', 0)
            supervisor = zone_info.get('personnel', {}).get('shift_supervisor', 'N/A')
            
            formatted_zones.append(f"""
ZONE {zone.upper()}:
  Personnel: {personnel_count} (Superviseur: {supervisor})
  Statut général: {zone_info.get('status', 'unknown')}
  Capteurs:
{chr(10).join(sensors)}""")
        
        # Conditions météorologiques
        weather_text = f"""
CONDITIONS MÉTÉO:
- Température: {weather.temperature:.1f}°C
- Humidité: {weather.humidity:.1f}%
- Vent: {weather.wind_speed:.1f}m/s, direction {weather.wind_direction:.0f}°
- Pression: {weather.pressure:.1f}hPa
- Visibilité: {weather.visibility:.1f}km
- Précipitations: {weather.precipitation:.1f}mm/h"""
        
        # Métriques de production
        production_text = f"""
PRODUCTION ACTUELLE:
- Cadence: {production.hourly_production:.1f} tonnes/h
- Qualité P2O5: {production.quality_grade:.1f}%
- Consommation énergie: {production.energy_consumption:.0f} kWh
- Usage eau: {production.water_usage:.1f} m³/h  
- Déchets: {production.waste_generated:.1f} tonnes/h
- Efficacité: {production.efficiency_rate:.1%}"""
        
        return f"{chr(10).join(formatted_zones)}\n{weather_text}\n{production_text}"
    
    def _get_enhanced_context(self) -> str:
        """Contexte historique enrichi"""
        if not self.context_memory:
            return "Aucun historique disponible"
        
        # Analyser les tendances récentes
        recent_analyses = list(self.context_memory)[-5:]
        
        trend_analysis = []
        risk_progression = []
        
        for i, entry in enumerate(recent_analyses):
            analysis = entry["analysis"]
            timestamp = entry["timestamp"]
            current_risk = analysis.get("risk_assessment", {}).get("current_level", "UNKNOWN")
            
            trend_analysis.append(f"  {timestamp[-8:-3]}: {current_risk}")
            risk_progression.append(current_risk)
        
        # Détecter les patterns
        pattern_info = ""
        if len(set(risk_progression)) == 1:
            pattern_info = f"Pattern stable: {risk_progression[0]}"
        elif "CRITICAL" in risk_progression or "EMERGENCY" in risk_progression:
            pattern_info = "Pattern d'escalade détecté"
        
        return f"""
HISTORIQUE RÉCENT:
{chr(10).join(trend_analysis)}

ANALYSE PATTERN: {pattern_info}
ANALYSES TOTALES EN MÉMOIRE: {len(self.context_memory)}"""
    
    def _calculate_data_quality(self, readings: Dict[str, SensorReading]) -> float:
        """Calcule la qualité des données capteurs"""
        total_sensors = len(readings)
        if total_sensors == 0:
            return 0.0
        
        quality_factors = {
            SensorStatus.NORMAL: 1.0,
            SensorStatus.WARNING: 0.8,
            SensorStatus.CRITICAL: 0.6,
            SensorStatus.OFFLINE: 0.0
        }
        
        total_quality = sum(quality_factors.get(reading.status, 0.5) for reading in readings.values())
        
        # Pénalité pour capteurs en maintenance
        maintenance_penalty = sum(0.1 for reading in readings.values() if reading.maintenance_due)
        
        return max(0.0, min(1.0, total_quality / total_sensors - maintenance_penalty / total_sensors))
    
    def _assess_environmental_impact(self, weather: WeatherCondition) -> Dict[str, Any]:
        """Évalue l'impact environnemental"""
        impact = {
            "dust_dispersion_risk": "low",
            "gas_containment_risk": "low", 
            "visibility_impact": "minimal",
            "population_exposure_risk": "low"
        }
        
        # Analyse du vent pour dispersion
        if weather.wind_speed > 10:
            impact["dust_dispersion_risk"] = "high"
            impact["gas_containment_risk"] = "moderate"
        elif weather.wind_speed > 6:
            impact["dust_dispersion_risk"] = "moderate"
        
        # Visibilité
        if weather.visibility < 1:
            impact["visibility_impact"] = "severe"
        elif weather.visibility < 3:
            impact["visibility_impact"] = "moderate"
        
        # Risque population (direction vent vers villages)
        if 90 <= weather.wind_direction <= 270:  # Vent vers villages
            if weather.wind_speed > 5:
                impact["population_exposure_risk"] = "moderate"
                if weather.wind_speed > 12:
                    impact["population_exposure_risk"] = "high"
        
        return impact
    
    def _create_sensor_summary(self, readings: Dict[str, SensorReading]) -> Dict[str, Any]:
        """Crée un résumé des capteurs"""
        summary = {
            "total_sensors": len(readings),
            "status_distribution": {"normal": 0, "warning": 0, "critical": 0, "offline": 0},
            "zones_affected": set(),
            "maintenance_required": 0,
            "critical_sensors": []
        }
        
        for reading in readings.values():
            summary["status_distribution"][reading.status.value] += 1
            
            if reading.status != SensorStatus.NORMAL:
                summary["zones_affected"].add(reading.zone)
            
            if reading.maintenance_due:
                summary["maintenance_required"] += 1
            
            if reading.status == SensorStatus.CRITICAL:
                summary["critical_sensors"].append({
                    "sensor_id": reading.sensor_id,
                    "value": reading.value,
                    "location": reading.location,
                    "zone": reading.zone
                })
        
        summary["zones_affected"] = list(summary["zones_affected"])
        return summary
    
    async def execute_advanced_protocol(self, protocol_name: str, 
                                      context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute un protocole avec adaptation contextuelle"""
        if protocol_name not in self.emergency_protocols:
            return {"error": f"Protocole {protocol_name} non trouvé"}
        
        protocol = self.emergency_protocols[protocol_name]
        
        # Adapter le protocole au contexte
        adapted_actions = await self._adapt_protocol_to_context(protocol, context_data)
        
        execution_log = []
        start_time = datetime.now()
        
        try:
            for i, action_detail in enumerate(adapted_actions):
                # Simulation d'exécution avec temps réalistes
                execution_time = action_detail.get("estimated_time", 30)
                await asyncio.sleep(min(execution_time / 30, 2))  # Simulation accélérée
                
                success_probability = action_detail.get("success_probability", 0.95)
                success = random.random() < success_probability
                
                log_entry = {
                    "step": i + 1,
                    "action": action_detail["action"],
                    "status": "completed" if success else "failed",
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": execution_time,
                    "personnel_assigned": action_detail.get("personnel_needed", 1),
                    "equipment_used": action_detail.get("equipment", [])
                }
                
                execution_log.append(log_entry)
                
                if success:
                    logger.info(f"✅ Action {i+1} réussie: {action_detail['action'][:50]}...")
                else:
                    logger.warning(f"❌ Action {i+1} échouée: {action_detail['action'][:50]}...")
                    # En cas d'échec, actions de contingence
                    if "contingency" in action_detail:
                        contingency_log = await self._execute_contingency(action_detail["contingency"])
                        execution_log.extend(contingency_log)
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            # Enregistrer l'intervention
            intervention_record = {
                "protocol": protocol,
                "execution_log": execution_log,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration": total_duration,
                "context": context_data,
                "success_rate": len([l for l in execution_log if l["status"] == "completed"]) / len(execution_log)
            }
            
            self.active_protocols.append(intervention_record)
            
            # Apprentissage: enregistrer le succès
            if intervention_record["success_rate"] > 0.8:
                self.learning_data["successful_interventions"].append(intervention_record)
            
            return {
                "protocol_executed": protocol_name,
                "total_actions": len(adapted_actions),
                "success_rate": intervention_record["success_rate"],
                "total_duration": total_duration,
                "execution_log": execution_log,
                "adaptations_made": len([a for a in adapted_actions if "adapted" in a]),
                "personnel_mobilized": sum(a.get("personnel_needed", 1) for a in adapted_actions),
                "estimated_cost": self._estimate_intervention_cost(adapted_actions)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du protocole: {e}")
            return {"error": str(e), "partial_execution": execution_log}
    
    async def _adapt_protocol_to_context(self, protocol: EmergencyProtocol, 
                                       context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Adapte un protocole au contexte spécifique"""
        adapted_actions = []
        
        weather = context.get("weather", {})
        zone_status = context.get("zone_status", {})
        sensor_data = context.get("sensor_readings", {})
        
        for action in protocol.required_actions:
            action_detail = {
                "action": action,
                "estimated_time": 30,  # Temps par défaut
                "personnel_needed": 2,
                "equipment": [],
                "success_probability": 0.95
            }
            
            # Adaptations contextuelles
            if "évacuation" in action.lower():
                # Adapter l'évacuation selon météo et zones
                if weather.get("wind_speed", 0) > 10:
                    action_detail["action"] += " (route adaptée vent fort)"
                    action_detail["estimated_time"] = 45
                
                affected_zones = context.get("affected_zones", [])
                personnel_count = sum(zone_status.get(zone, {}).get("personnel", {}).get("personnel_count", 0) 
                                    for zone in affected_zones)
                action_detail["personnel_needed"] = max(3, personnel_count // 4)
            
            elif "ventilation" in action.lower():
                # Adapter selon conditions météo
                if weather.get("wind_speed", 0) < 2:
                    action_detail["action"] += " (ventilation forcée nécessaire)"
                    action_detail["estimated_time"] = 60
                    action_detail["equipment"].append("Ventilateurs industriels")
            
            elif "isolation" in action.lower():
                # Adapter selon type de capteurs en alarme
                critical_sensors = [s for s, data in sensor_data.items() 
                                  if isinstance(data, dict) and data.get("status") == "critical"]
                if len(critical_sensors) > 3:
                    action_detail["action"] += " (isolation multiple nécessaire)"
                    action_detail["estimated_time"] = 90
                    action_detail["personnel_needed"] = 4
            
            # Ajouter contingences
            if action_detail["success_probability"] < 0.9:
                action_detail["contingency"] = f"Plan B pour: {action}"
            
            adapted_actions.append(action_detail)
        
        return adapted_actions
    
    async def _execute_contingency(self, contingency_action: str) -> List[Dict[str, Any]]:
        """Exécute une action de contingence"""
        contingency_log = [{
            "step": "contingency",
            "action": contingency_action,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "execution_time": 15,
            "note": "Action de contingence automatique"
        }]
        
        await asyncio.sleep(0.5)  # Simulation
        logger.info(f"🔄 Contingence activée: {contingency_action}")
        
        return contingency_log
    
    def _estimate_intervention_cost(self, actions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Estime le coût d'une intervention"""
        personnel_cost = sum(a.get("personnel_needed", 1) * a.get("estimated_time", 30) for a in actions) * 0.5  # 0.5€/minute/personne
        equipment_cost = len([e for a in actions for e in a.get("equipment", [])]) * 500  # 500€ par équipement
        
        return {
            "personnel_cost_eur": personnel_cost,
            "equipment_cost_eur": equipment_cost,
            "total_estimated_eur": personnel_cost + equipment_cost,
            "production_loss_eur": 1500 * sum(a.get("estimated_time", 30) for a in actions) / 60  # 1500€/h de perte
        }

class MineEmergencySystem:
    """Système principal de gestion d'urgence avancé"""
    
    def __init__(self, claude_api_key: str):
        self.data_simulator = AdvancedPhosphateMineSimulator()
        self.ai_agent = EnhancedClaudeAgent(claude_api_key)
        self.monitoring_active = True
        self.system_status = "ACTIVE"
        
        # Pré-initialisation des données
        self._initialize_data()

    def _initialize_data(self):
        """Pré-initialise les données pour un démarrage rapide"""
        # Générer des données initiales
        self.current_analysis = {
            "risk_assessment": {"current_level": "NORMAL", "confidence_score": 0.95},
            "zone_analysis": {"affected_zones": [], "safe_zones": ["extraction", "traitement", "stockage"]}
        }
        
        # Initialiser les statistiques
        self.stats = {
            "total_analyses": 0,
            "protocols_executed": 0,
            "false_alarms_prevented": 0,
            "uptime_start": datetime.now(),
        }
        
        # Pré-charger quelques données historiques
        self.alerts_queue = deque(maxlen=50)
        for sensor_id in self.data_simulator.sensors_config.keys():
            readings = self.data_simulator.get_all_sensor_readings()
            if sensor_id in readings:
                self.data_simulator.sensor_history[sensor_id].append(readings[sensor_id])

    async def start_advanced_monitoring(self):
        """Démarre la surveillance avancée"""
        self.monitoring_active = True
        self.system_status = "ACTIVE"
        logger.info("🚀 Système de surveillance avancé démarré")
        
        while self.monitoring_active:
            try:
                cycle_start = datetime.now()
                
                # Obtenir toutes les données
                sensor_readings = self.data_simulator.get_all_sensor_readings()
                zone_status = self.data_simulator.get_zone_status()
                weather = self.data_simulator.weather
                production = self.data_simulator.production
                
                # Sauvegarder en base
                for reading in sensor_readings.values():
                    self.db_manager.save_sensor_reading(reading)
                
                # Analyse IA complète
                context_data = {
                    "sensor_readings": {k: v.to_dict() for k, v in sensor_readings.items()},
                    "weather": asdict(weather),
                    "production": asdict(production),
                    "zone_status": zone_status
                }
                
                analysis = await self.ai_agent.analyze_comprehensive_data(
                    sensor_readings, weather, production, zone_status
                )
                
                self.current_analysis = analysis
                self.stats["total_analyses"] += 1
                
                # Traitement des alertes
                await self._process_alerts(analysis, context_data)
                
                # Affichage du statut
                self._display_advanced_status(sensor_readings, analysis, zone_status)
                
                # Gestion des protocoles d'urgence
                protocol_needed = analysis.get("protocol_recommendation", {}).get("protocol_needed")
                if protocol_needed and analysis.get("risk_assessment", {}).get("current_level") == "EMERGENCY":
                    logger.warning(f"🚨 URGENCE - Activation protocole: {protocol_needed}")
                    execution_result = await self.ai_agent.execute_advanced_protocol(protocol_needed, context_data)
                    self.stats["protocols_executed"] += 1
                    
                    # Enregistrer l'exécution
                    self.alerts_queue.append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "PROTOCOL_EXECUTED",
                        "protocol": protocol_needed,
                        "result": execution_result
                    })
                
                # Mesure des performances du cycle
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                
                # Attendre le prochain cycle (adaptation dynamique)
                base_interval = 8  # 8 secondes de base
                risk_multiplier = {"NORMAL": 1.0, "WARNING": 0.7, "CRITICAL": 0.4, "EMERGENCY": 0.1}
                current_risk = analysis.get("risk_assessment", {}).get("current_level", "NORMAL")
                interval = base_interval * risk_multiplier.get(current_risk, 1.0)
                
                await asyncio.sleep(max(1, interval - cycle_duration))
                
            except Exception as e:
                logger.error(f"Erreur dans le cycle de surveillance avancé: {e}")
                self.system_status = "ERROR"
                await asyncio.sleep(5)
                self.system_status = "ACTIVE"
    
    async def _process_alerts(self, analysis: Dict[str, Any], context_data: Dict[str, Any]):
        """Traite les alertes et notifications"""
        risk_level = analysis.get("risk_assessment", {}).get("current_level", "NORMAL")
        
        # Alertes préventives
        predictive_alerts = analysis.get("predictive_alerts", [])
        for alert in predictive_alerts:
            if alert.get("probability", 0) > 0.7:  # Probabilité élevée
                self.alerts_queue.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "PREDICTIVE_ALERT",
                    "timeframe": alert.get("timeframe"),
                    "scenario": alert.get("scenario"),
                    "probability": alert.get("probability"),
                    "measures": alert.get("preventive_measures", [])
                })
                
                logger.warning(f"⚠️ Alerte prédictive: {alert.get('scenario')} dans {alert.get('timeframe')}")
        
        # Corrélations dangereuses
        correlations = analysis.get("correlations_detected", [])
        for correlation in correlations:
            if correlation.get("risk_amplification") and "élevé" in str(correlation.get("risk_amplification")).lower():
                self.alerts_queue.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "CORRELATION_ALERT",
                    "correlation": correlation
                })
        
        # Prévention fausses alarmes
        confidence = analysis.get("risk_assessment", {}).get("confidence_score", 0)
        if risk_level in ["CRITICAL", "EMERGENCY"] and confidence < 0.6:
            logger.info("🛡️ Possible fausse alarme détectée - Analyse approfondie requise")
            self.stats["false_alarms_prevented"] += 1
    
    def _display_advanced_status(self, readings: Dict[str, SensorReading], 
                               analysis: Dict[str, Any], zone_status: Dict[str, Dict]):
        """Affiche le statut avancé du système"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        risk_current = analysis.get("risk_assessment", {}).get("current_level", "UNKNOWN")
        risk_predicted = analysis.get("risk_assessment", {}).get("predicted_level_2h", "UNKNOWN")
        confidence = analysis.get("risk_assessment", {}).get("confidence_score", 0)
        
        print(f"\n{'='*80}")
        print(f"🏭 MINE DE PHOSPHATE MAROC - SURVEILLANCE AVANCÉE [{timestamp}]")
        print(f"{'='*80}")
        print(f"🚦 RISQUE ACTUEL: {risk_current} | PRÉDICTION 2H: {risk_predicted} | CONFIANCE: {confidence:.2f}")
        print(f"📊 ANALYSES: {self.stats['total_analyses']} | PROTOCOLES: {self.stats['protocols_executed']}")
        
        # Statut par zone
        print(f"\n📍 STATUT PAR ZONE:")
        for zone_name, zone_info in zone_status.items():
            status_icon = {"normal": "🟢", "warning": "🟡", "critical": "🔴", "degraded": "🟠"}.get(zone_info["status"], "⚫")
            personnel = zone_info.get("personnel", {}).get("personnel_count", 0)
            print(f"   {status_icon} {zone_name.upper()}: {zone_info['status']} ({personnel} pers.)")
        
        # Alertes récentes
        recent_alerts = list(self.alerts_queue)[-3:]
        if recent_alerts:
            print(f"\n🔔 ALERTES RÉCENTES:")
            for alert in recent_alerts:
                alert_time = alert["timestamp"][-8:-3]
                alert_type = alert["type"]
                print(f"   {alert_time}: {alert_type}")
        
        # Météo impact
        weather = self.data_simulator.weather
        weather_impact = "🌤️ FAVORABLE"
        if weather.wind_speed > 12:
            weather_impact = "🌪️ VENT FORT"
        elif weather.visibility < 2:
            weather_impact = "🌫️ VISIBILITÉ RÉDUITE"
        
        print(f"\n🌍 MÉTÉO: {weather_impact} | Vent: {weather.wind_speed:.1f}m/s | Vis: {weather.visibility:.1f}km")
        
        # Production
        efficiency = self.data_simulator.production.efficiency_rate
        efficiency_icon = "🟢" if efficiency > 0.8 else "🟡" if efficiency > 0.6 else "🔴"
        print(f"⚙️ PRODUCTION: {efficiency_icon} {efficiency:.1%} | {self.data_simulator.production.hourly_production:.0f}t/h")
        
        # Capteurs critiques
        critical_count = len([r for r in readings.values() if r.status == SensorStatus.CRITICAL])
        if critical_count > 0:
            print(f"\n🔴 CAPTEURS CRITIQUES: {critical_count}")
            for sensor_id, reading in readings.items():
                if reading.status == SensorStatus.CRITICAL:
                    print(f"   - {sensor_id}: {reading.value} {reading.unit} @ {reading.location}")
    
    def trigger_advanced_scenario(self, scenario_type: str, intensity: str = "moderate"):
        """Déclenche un scénario de test avancé"""
        scenarios = {
            "dust_storm": "dust_storm_impact",
            "chemical_cascade": "chemical_leak_cascade", 
            "equipment_chain": "equipment_failure_chain"
        }
        
        intensity_duration = {"low": 2, "moderate": 5, "high": 8, "extreme": 12}
        
        if scenario_type in scenarios:
            duration = intensity_duration.get(intensity, 5)
            self.data_simulator.trigger_anomaly(scenarios[scenario_type], duration, intensity)
            
            self.alerts_queue.append({
                "timestamp": datetime.now().isoformat(),
                "type": "SCENARIO_TRIGGERED",
                "scenario": scenario_type,
                "intensity": intensity,
                "duration": duration
            })
            
            logger.info(f"🧪 Scénario avancé déclenché: {scenario_type} (intensité: {intensity}, durée: {duration})")
        else:
            logger.error(f"Scénario inconnu: {scenario_type}")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du système"""
        uptime = datetime.now() - self.stats["uptime_start"]
        
        return {
            "system_status": self.system_status,
            "uptime_hours": uptime.total_seconds() / 3600,
            "total_analyses": self.stats["total_analyses"],
            "protocols_executed": self.stats["protocols_executed"],
            "false_alarms_prevented": self.stats["false_alarms_prevented"],
            "current_risk_level": self.current_analysis.get("risk_assessment", {}).get("current_level") if self.current_analysis else "UNKNOWN",
            "alerts_in_queue": len(self.alerts_queue),
            "data_quality": self.current_analysis.get("data_quality_score", 0) if self.current_analysis else 0,
            "active_anomalies": len(self.data_simulator.active_anomalies),
            "zones_status": self.data_simulator.get_zone_status(),
            "weather_conditions": asdict(self.data_simulator.weather),
            "production_metrics": asdict(self.data_simulator.production)
        }
    
    def get_alerts_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Retourne l'historique des alertes"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_alerts = []
        for alert in self.alerts_queue:
            alert_time = datetime.fromisoformat(alert["timestamp"])
            if alert_time >= cutoff_time:
                filtered_alerts.append(alert)
        
        return sorted(filtered_alerts, key=lambda x: x["timestamp"], reverse=True)
    
    def get_sensor_trends(self, sensor_id: str, hours: int = 6) -> Dict[str, Any]:
        """Analyse les tendances d'un capteur"""
        if sensor_id not in self.data_simulator.sensor_history:
            return {"error": f"Capteur {sensor_id} non trouvé"}
        
        history = list(self.data_simulator.sensor_history[sensor_id])
        if len(history) < 2:
            return {"error": "Historique insuffisant"}
        
        # Calcul des tendances
        recent_values = [reading.value for reading in history[-10:]]  # 10 dernières valeurs
        older_values = [reading.value for reading in history[-20:-10]] if len(history) >= 20 else recent_values
        
        recent_avg = np.mean(recent_values)
        older_avg = np.mean(older_values) if older_values else recent_avg
        
        trend_direction = "stable"
        trend_percentage = 0
        
        if recent_avg > older_avg * 1.1:
            trend_direction = "increasing"
            trend_percentage = ((recent_avg - older_avg) / older_avg) * 100
        elif recent_avg < older_avg * 0.9:
            trend_direction = "decreasing"
            trend_percentage = ((older_avg - recent_avg) / older_avg) * 100
        
        return {
            "sensor_id": sensor_id,
            "current_value": history[-1].value,
            "unit": history[-1].unit,
            "trend_direction": trend_direction,
            "trend_percentage": round(trend_percentage, 2),
            "recent_average": round(recent_avg, 2),
            "volatility": round(np.std(recent_values), 2),
            "status": history[-1].status.value,
            "readings_count": len(history)
        }
    
    def stop_monitoring(self):
        """Arrête la surveillance"""
        self.monitoring_active = False
        self.system_status = "STOPPED"
        logger.info("⏹️ Système de surveillance arrêté")
    
    def export_data(self, format_type: str = "json", hours: int = 24) -> str:
        """Exporte les données système"""
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "system_stats": self.get_system_statistics(),
            "alerts_history": self.get_alerts_history(hours),
            "current_analysis": self.current_analysis,
            "sensor_summaries": {}
        }
        
        # Ajouter résumés des capteurs
        for sensor_id in self.data_simulator.sensors_config.keys():
            export_data["sensor_summaries"][sensor_id] = self.get_sensor_trends(sensor_id, hours)
        
        if format_type == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            return str(export_data)  # Format basique pour autres types