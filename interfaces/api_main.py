# interfaces/api_main.py
import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from colorama import Fore, Style 
from datetime import datetime # Import ajouté si non présent

# Ajout du répertoire parent au path pour les imports relatifs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des composants du coeur
from core.evenement import Evenement, LISTE_EVENEMENTS_INVENTAIRE 
from utils.persistence import charger_inventaire, sauvegarder_inventaire

# Définition du chemin racine et du fichier de log
CHEMIN_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(CHEMIN_RACINE, 'app.log')

# === CONFIGURATION DU LOGGING ===
def setup_logging():
    """Configure la journalisation dans la console et dans le fichier app.log."""
    logger = logging.getLogger('IA_Assistant')
    logger.setLevel(logging.INFO) 

    # Handler pour écrire dans un fichier avec rotation (utile sur serveur)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Ajout du handler si pas déjà présent
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        logger.addHandler(handler)
        
    # Handler pour la console (important pour le débogage local et le déploiement Cloud)
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

# Activation de CORS
CORS(app) 

# Chargement initial de l'inventaire au démarrage de l'API
LISTE_EVENEMENTS_INVENTAIRE.extend(charger_inventaire())
logger.info(f"API initialisée. {len(LISTE_EVENEMENTS_INVENTAIRE)} événements chargés.")


@app.route('/', methods=['GET'])
def home():
    """Endpoint principal. Renvoie le template HTML de l'application mobile."""
    logger.info("Accès à la page d'accueil (index.html)")
    return render_template('index.html')


@app.route('/api/v1/taches/priorite', methods=['GET'])
def get_taches_prioritaires():
    """
    Retourne la liste des tâches actives, triées par score de priorité.
    """
    try:
        taches_actives = [e for e in LISTE_EVENEMENTS_INVENTAIRE if e.type_event == 'Tache' and not e.est_complete]
        
        taches_avec_score = [{"tache": t, "score": t.calculer_score_priorite()} for t in taches_actives]
        suggestions = sorted(taches_avec_score, key=lambda x: x["score"], reverse=True)
        
        resultat = []
        for item in suggestions:
            tache_dict = item["tache"].to_dict()
            tache_dict['score_priorite'] = round(item['score'], 2)
            tache_dict['id'] = item["tache"].db_id # Utilise l'ID de la DB pour le frontend
            resultat.append(tache_dict)

        logger.info(f"Retour de {len(resultat)} tâches prioritaires.")
        return jsonify(resultat)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tâches prioritaires: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne lors de la priorisation."}), 500


@app.route('/api/v1/taches/ajouter', methods=['POST'])
def ajouter_tache_api():
    """
    Accepte les données d'une nouvelle tâche via POST et l'ajoute à l'inventaire.
    """
    try:
        data = request.json
        if not data or not data.get('nom'):
            logger.warning("Tentative d'ajout de tâche sans nom.")
            return jsonify({"error": "Nom de tâche manquant."}), 400

        # Mappage des champs de l'API aux champs de la dataclass Evenement
        nouvelle_tache = Evenement(
            nom=data.get('nom'), 
            type_event='Tache', 
            urgence=int(data.get('urgence', 3)), 
            importance=int(data.get('importance', 3)), 
            duree_totale_minutes=int(data.get('duree', 60)),
            projet=data.get('projet', 'Divers')
        )
        
        LISTE_EVENEMENTS_INVENTAIRE.append(nouvelle_tache)
        sauvegarder_inventaire(LISTE_EVENEMENTS_INVENTAIRE)

        logger.info(f"Tâche ajoutée: '{nouvelle_tache.nom}' (ID: {nouvelle_tache.db_id})")
        return jsonify({"message": f"Tâche '{nouvelle_tache.nom}' ajoutée.", "tache": nouvelle_tache.to_dict()}), 201

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de tâche via API: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de l'ajout."}), 500


@app.route('/api/v1/taches/<int:tache_id>/terminer', methods=['POST'])
def terminer_tache_api(tache_id):
    """
    Marque une tâche comme terminée en utilisant son ID unique de la DB.
    """
    try:
        tache_a_terminer = next(
            (e for e in LISTE_EVENEMENTS_INVENTAIRE if e.db_id == tache_id and e.type_event == 'Tache'),
            None
        )
        
        if tache_a_terminer and not tache_a_terminer.est_complete:
            tache_a_terminer.marquer_terminee()
            sauvegarder_inventaire(LISTE_EVENEMENTS_INVENTAIRE)
            logger.info(f"Tâche terminée: '{tache_a_terminer.nom}' (ID: {tache_id})")
            return jsonify({"message": f"Tâche '{tache_a_terminer.nom}' marquée comme terminée."}), 200
        
        logger.warning(f"Tentative de terminer une tâche invalide (ID: {tache_id}).")
        return jsonify({"error": "ID de tâche invalide, non trouvée ou déjà terminée."}), 404
    
    except Exception as e:
        logger.error(f"Erreur lors de la terminaison de tâche via API (ID: {tache_id}): {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de la mise à jour."}), 500


if __name__ == '__main__':
    # Le mode debug=True est uniquement pour le développement local
    logger.info(f"Démarrage de l'API en mode développement sur http://0.0.0.0:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)