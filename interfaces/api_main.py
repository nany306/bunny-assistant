# interfaces/api_main.py
import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from colorama import Fore, Style 
from datetime import datetime

# Ajout du répertoire parent au path pour les imports relatifs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des composants du coeur (LISTE_EVENEMENTS_INVENTAIRE n'est plus utilisé)
from core.evenement import Evenement, EvenementSchema

# --- IMPORT UNIQUE ---
# Nous n'avons plus besoin de persistence.py, les données arrivent directement
# en JSON dans le corps de la requête.
# --------------------

# Définition du chemin racine et du fichier de log
CHEMIN_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(CHEMIN_RACINE, 'app.log')

# === CONFIGURATION DU LOGGING (Inchangée) ===
def setup_logging():
    """Configure la journalisation dans la console et dans le fichier app.log."""
    # ... (Code de setup_logging inchangé) ...
    logger = logging.getLogger('IA_Assistant')
    logger.setLevel(logging.INFO) 
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        logger.addHandler(handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
         logger.addHandler(stream_handler)
    return logger

# Initialisation du logger
logger = setup_logging()
# =================================

# Initialisation de l'application Flask
app = Flask(__name__, template_folder=os.path.join(CHEMIN_RACINE, 'templates'))
CORS(app) 

# Le schéma Marshmallow pour gérer la sérialisation/désérialisation
evenement_schema = EvenementSchema()
evenements_schema = EvenementSchema(many=True)

# -----------------------------------------------------------
# FONCTION UTILITAIRE : Charger les objets Evenement depuis le JSON reçu
# -----------------------------------------------------------
def charger_evenements_depuis_json(json_data):
    """Charge une liste d'objets Evenement à partir d'une liste de dicts JSON."""
    try:
        # Désérialisation directe des dicts en objets Evenement
        liste_evenements = evenements_schema.load(json_data)
        return liste_evenements
    except Exception as e:
        logger.error(f"Erreur de désérialisation JSON en objets Evenement: {e}", exc_info=True)
        return []

# -----------------------------------------------------------
# ENDPOINTS API (MODIFIÉS)
# -----------------------------------------------------------

@app.route('/', methods=['GET'])
def home():
    """Endpoint principal. Renvoie le template HTML de l'application mobile."""
    logger.info("Accès à la page d'accueil (index.html)")
    return render_template('index.html')


@app.route('/api/v1/taches/priorite', methods=['POST'])
def get_taches_prioritaires():
    """
    Retourne la liste des tâches actives triées par score. 
    Reçoit la liste complète des événements en POST.
    """
    try:
        data = request.json
        if not data or 'inventaire' not in data:
            logger.warning("Requête de priorisation sans inventaire fourni.")
            return jsonify({"error": "Inventaire manquant dans le corps de la requête."}), 400
            
        # 1. Charger les événements depuis le JSON reçu
        inventaire_complet = charger_evenements_depuis_json(data['inventaire'])
        
        taches_actives = [e for e in inventaire_complet if e.type_event == 'Tache' and not e.est_complete]
        
        taches_avec_score = [{"tache": t, "score": t.calculer_score_priorite()} for t in taches_actives]
        suggestions = sorted(taches_avec_score, key=lambda x: x["score"], reverse=True)
        
        resultat = []
        for item in suggestions:
            # Sérialisation vers un dict pour l'envoi au client
            tache_dict = evenement_schema.dump(item["tache"])
            tache_dict['score_priorite'] = round(item['score'], 2)
            resultat.append(tache_dict)

        logger.info(f"Priorisation effectuée. Retour de {len(resultat)} tâches.")
        # L'inventaire complet n'est pas retourné ici, seulement la liste prioritaire.
        return jsonify(resultat)
        
    except Exception as e:
        logger.error(f"Erreur lors de la priorisation via POST: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne lors de la priorisation."}), 500


@app.route('/api/v1/taches/ajouter', methods=['POST'])
def ajouter_tache_api():
    """
    Ajoute une nouvelle tâche et retourne l'inventaire complet mis à jour.
    Reçoit l'inventaire actuel et les données de la nouvelle tâche en POST.
    """
    try:
        data = request.json
        if not data or 'inventaire' not in data or not data.get('nom'):
            logger.warning("Requête d'ajout incomplète.")
            return jsonify({"error": "Données (inventaire, nom) manquantes."}), 400
        
        # 1. Charger l'inventaire existant
        inventaire_complet = charger_evenements_depuis_json(data['inventaire'])
        
        # 2. Créer et ajouter la nouvelle tâche
        nouvelle_tache = Evenement(
            nom=data.get('nom'), 
            type_event='Tache', 
            urgence=int(data.get('urgence', 3)), 
            importance=int(data.get('importance', 3)), 
            duree_totale_minutes=int(data.get('duree', 60)),
            projet=data.get('projet', 'Divers')
        )
        
        inventaire_complet.append(nouvelle_tache)
        
        # 3. Sérialiser et retourner l'inventaire complet mis à jour
        inventaire_mis_a_jour_json = evenements_schema.dump(inventaire_complet)

        logger.info(f"Tâche ajoutée: '{nouvelle_tache.nom}'. Inventaire total: {len(inventaire_complet)}")
        
        # On retourne l'inventaire complet. Le client doit le sauvegarder.
        return jsonify(inventaire_mis_a_jour_json), 201

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de tâche (Stateless): {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de l'ajout."}), 500


@app.route('/api/v1/taches/terminer', methods=['POST'])
def terminer_tache_api():
    """
    Marque une tâche comme terminée et retourne l'inventaire complet mis à jour.
    Reçoit l'inventaire actuel et l'ID de la tâche en POST.
    """
    try:
        data = request.json
        if not data or 'inventaire' not in data or 'db_id' not in data:
            logger.warning("Requête de terminaison incomplète.")
            return jsonify({"error": "Données (inventaire, db_id) manquantes."}), 400
        
        db_id_a_terminer = data['db_id']
        inventaire_complet = charger_evenements_depuis_json(data['inventaire'])
        
        tache_a_terminer = next(
            (e for e in inventaire_complet if e.db_id == db_id_a_terminer and e.type_event == 'Tache'),
            None
        )
        
        if tache_a_terminer and not tache_a_terminer.est_complete:
            tache_a_terminer.marquer_terminee()
            
            # 3. Sérialiser et retourner l'inventaire complet mis à jour
            inventaire_mis_a_jour_json = evenements_schema.dump(inventaire_complet)
            
            logger.info(f"Tâche terminée: '{tache_a_terminer.nom}' (ID: {db_id_a_terminer})")
            return jsonify(inventaire_mis_a_jour_json), 200
        
        logger.warning(f"Tentative de terminer une tâche invalide (ID: {db_id_a_terminer}).")
        return jsonify({"error": "ID de tâche invalide, non trouvée ou déjà terminée."}), 404
    
    except Exception as e:
        logger.error(f"Erreur lors de la terminaison de tâche (Stateless, ID: {db_id_a_terminer}): {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de la mise à jour."}), 500


if __name__ == '__main__':
    logger.info(f"Démarrage de l'API en mode développement sur http://0.0.0.0:5000/")
    # NOTE: En production, Gunicorn utilise cette variable, pas cette boucle if
    app.run(debug=True, host='0.0.0.0', port=5000)