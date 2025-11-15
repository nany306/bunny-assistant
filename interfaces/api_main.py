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

from core.evenement import Evenement, EvenementSchema, generate_unique_id

# Définition du chemin racine et du fichier de log
CHEMIN_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(CHEMIN_RACINE, 'app.log')

# === CONFIGURATION DU LOGGING ===
def setup_logging():
    logger = logging.getLogger('IA_Assistant')
    logger.setLevel(logging.INFO) 
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message.s)')
    handler.setFormatter(formatter)
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        logger.addHandler(handler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
         logger.addHandler(stream_handler)
    return logger

logger = setup_logging()
# =================================

app = Flask(__name__, template_folder=os.path.join(CHEMIN_RACINE, 'templates'))
CORS(app) 

evenement_schema = EvenementSchema()
evenements_schema = EvenementSchema(many=True)

# -----------------------------------------------------------
# FONCTION UTILITAIRE
# -----------------------------------------------------------
def charger_evenements_depuis_json(json_data):
    try:
        liste_evenements = evenements_schema.load(json_data)
        return liste_evenements
    except Exception as e:
        logger.error(f"Erreur de désérialisation JSON en objets Evenement: {e}", exc_info=True)
        return []

# -----------------------------------------------------------
# ENDPOINTS API 
# -----------------------------------------------------------

@app.route('/', methods=['GET'])
def home():
    logger.info("Accès à la page d'accueil (index.html)")
    return render_template('index.html')


@app.route('/api/v1/taches/priorite', methods=['POST'])
def get_taches_prioritaires():
    try:
        data = request.json
        if not data or 'inventaire' not in data:
            return jsonify({"error": "Inventaire manquant."}), 400
            
        inventaire_complet = charger_evenements_depuis_json(data['inventaire'])
        
        # On ne priorise que les 'Tache' non complétées.
        taches_actives = [
            e for e in inventaire_complet 
            if e.type_event == 'Tache' and not e.est_complete
        ]
        
        taches_avec_score = [{"tache": t, "score": t.calculer_score_priorite()} for t in taches_actives]
        suggestions = sorted(taches_avec_score, key=lambda x: x["score"], reverse=True)
        
        # On ne retourne que les objets Tache (sans le score, comme demandé)
        resultat = evenements_schema.dump([item["tache"] for item in suggestions])

        logger.info(f"Priorisation effectuée. Retour de {len(resultat)} tâches.")
        return jsonify(resultat)
        
    except Exception as e:
        logger.error(f"Erreur lors de la priorisation via POST: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne lors de la priorisation."}), 500


@app.route('/api/v1/taches/ajouter', methods=['POST'])
def ajouter_tache_api():
    try:
        data = request.json
        if not data or 'inventaire' not in data or not data.get('nom'):
            return jsonify({"error": "Données (inventaire, nom) manquantes."}), 400
        
        inventaire_complet = charger_evenements_depuis_json(data['inventaire'])
        
        # --- MISE À JOUR CALENDRIER ---
        # Conversion des dates ISO (string) en objets datetime si elles existent
        date_debut_obj = None
        if data.get('date_debut'):
            try:
                date_debut_obj = datetime.fromisoformat(data['date_debut'])
            except ValueError:
                logger.warning(f"Format date_debut invalide: {data['date_debut']}")
                date_debut_obj = datetime.now() # Fallback
        else:
            date_debut_obj = datetime.now()

        date_fin_obj = None
        if data.get('date_fin'):
            try:
                date_fin_obj = datetime.fromisoformat(data['date_fin'])
            except ValueError:
                logger.warning(f"Format date_fin invalide: {data['date_fin']}")
        
        nouvel_evenement = Evenement(
            nom=data.get('nom'), 
            type_event=data.get('type_event', 'Tache'), 
            urgence=int(data.get('urgence', 3)), 
            importance=int(data.get('importance', 3)), 
            duree_totale_minutes=int(data.get('duree', 60)),
            projet=data.get('projet', 'Divers'),
            db_id=generate_unique_id(),
            date_debut=date_debut_obj,
            date_fin=date_fin_obj
        )
        # -------------------------------
        
        inventaire_complet.append(nouvel_evenement)
        inventaire_mis_a_jour_json = evenements_schema.dump(inventaire_complet)

        logger.info(f"Événement ajouté: '{nouvel_evenement.nom}'. Inventaire total: {len(inventaire_complet)}")
        return jsonify(inventaire_mis_a_jour_json), 201

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout (Stateless): {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de l'ajout."}), 500


@app.route('/api/v1/taches/terminer', methods=['POST'])
def terminer_tache_api():
    try:
        data = request.json
        if not data or 'inventaire' not in data or 'db_id' not in data:
            return jsonify({"error": "Données (inventaire, db_id) manquantes."}), 400
        
        db_id_a_terminer = data['db_id']
        inventaire_complet = charger_evenements_depuis_json(data['inventaire'])
        
        tache_a_terminer = next(
            (e for e in inventaire_complet if e.db_id == db_id_a_terminer), None
        )
        
        if tache_a_terminer and not tache_a_terminer.est_complete:
            tache_a_terminer.marquer_terminee()
            
            inventaire_mis_a_jour_json = evenements_schema.dump(inventaire_complet)
            
            logger.info(f"Événement terminé: '{tache_a_terminer.nom}' (ID: {db_id_a_terminer})")
            return jsonify(inventaire_mis_a_jour_json), 200
        
        logger.warning(f"Tentative de terminer une tâche invalide (ID: {db_id_a_terminer}).")
        return jsonify({"error": "ID d'événement invalide, non trouvé ou déjà terminé."}), 404
    
    except Exception as e:
        logger.error(f"Erreur lors de la terminaison (Stateless, ID: {db_id_a_terminer}): {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de la mise à jour."}), 500


# (Le endpoint /api/v1/data/dump reste inchangé, si vous l'avez)

if __name__ == '__main__':
    logger.info(f"Démarrage de l'API en mode développement sur http://0.0.0.0:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)