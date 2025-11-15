import os
import json
import logging
import sys
from flask import Flask, render_template, request, jsonify

# --- 1. CONFIGURATION DU LOGGER (CORRECTION DE L'ERREUR) ---
# Ceci configure le logger pour utiliser le format standard et éviter le "KeyError: 'message.s'".
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# --- 2. INITIALISATION DE L'APPLICATION ---
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Définition du chemin des données (optionnel, mais propre)
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_PATH, exist_ok=True)

# --- 3. LOGIQUE MÉTIER DE BASE ---

def get_new_db_id(inventaire):
    """Calcule le prochain ID unique."""
    if not inventaire:
        return 1
    # On assure de prendre le max des IDs qui sont des entiers (les récurrents sont ignorés)
    current_ids = [item.get('db_id') for item in inventaire if isinstance(item.get('db_id'), int)]
    return max(current_ids) + 1 if current_ids else 1

def calculate_priority(importance, urgence):
    """Calcule une priorité simple (ex: 1=faible, 2=moyen, 3=élevé) basée sur une matrice de 1 à 5."""
    if importance >= 4 and urgence >= 4:
        return 'high'
    if importance >= 3 or urgence >= 3:
        return 'medium'
    return 'low'

# --- 4. ROUTES FLASK ---

@app.route('/')
def home():
    """Route pour servir la page d'accueil (index.html)."""
    # L'appel au logger fonctionne maintenant correctement grâce à la correction ci-dessus.
    logger.info("Accès à la page d'accueil (index.html)")
    return render_template('index.html')

@app.route('/api/v1/taches/priorite', methods=['POST'])
def get_priorites():
    """Endpoint pour calculer et retourner la liste des tâches par priorité."""
    data = request.get_json()
    inventaire = data.get('inventaire', [])
    
    # Filtrer uniquement les tâches non complétées et non datées/récurrentes pour la priorisation
    taches_actives = [
        t for t in inventaire 
        if t.get('est_complete') is not True and t.get('type_event') == 'Tache'
    ]
    
    # Appliquer un calcul de score ou utiliser les champs importance/urgence directement
    # Nous allons ici trier par (importance + urgence) décroissant
    taches_actives.sort(
        key=lambda t: (t.get('importance', 0) + t.get('urgence', 0), t.get('db_id')), 
        reverse=True
    )
    
    # Renvoyer l'inventaire filtré et trié
    return jsonify(taches_actives)

@app.route('/api/v1/taches/ajouter', methods=['POST'])
def ajouter_tache():
    """Endpoint pour ajouter une nouvelle tâche/événement."""
    try:
        data = request.get_json()
        inventaire = data.get('inventaire', [])
        
        # Validation minimale
        if not data.get('nom') or not data.get('duree'):
            return jsonify({"error": "Nom et durée sont requis"}), 400

        nouvel_id = get_new_db_id(inventaire)
        
        nouvel_evenement = {
            "db_id": nouvel_id,
            "nom": data.get('nom'),
            "type_event": data.get('type_event', 'Tache'),
            "importance": int(data.get('importance', 3)),
            "urgence": int(data.get('urgence', 3)),
            "duree_totale_minutes": int(data.get('duree')),
            "projet": data.get('projet', 'Divers'),
            "date_creation": os.environ.get('CURRENT_TIME', '2025-01-01T00:00:00Z'), # Placeholder, utiliser la date réelle côté client
            "est_complete": False,
            
            # Champs pour la planification
            "date_debut": data.get('date_debut'), # ISO string
            "date_fin": data.get('date_fin'),     # ISO string
            "recurrence": data.get('recurrence', 'none') # 'none', 'daily', 'weekly', 'monthly'
        }
        
        inventaire.append(nouvel_evenement)
        logger.info(f"Ajout de l'événement #{nouvel_id}: {nouvel_evenement['nom']}")
        
        return jsonify(inventaire)
    
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de la tâche: {e}")
        return jsonify({"error": f"Erreur interne: {e}"}), 500

@app.route('/api/v1/taches/terminer', methods=['POST'])
def terminer_tache():
    """Endpoint pour marquer une tâche comme terminée."""
    try:
        data = request.get_json()
        inventaire = data.get('inventaire', [])
        db_id_to_complete = data.get('db_id')
        
        # Trouver l'index de la tâche à compléter
        target_index = -1
        for i, item in enumerate(inventaire):
            # On cherche l'ID stocké (doit être un entier)
            if item.get('db_id') == db_id_to_complete:
                target_index = i
                break
        
        if target_index != -1:
            inventaire[target_index]['est_complete'] = True
            inventaire[target_index]['date_complete'] = os.environ.get('CURRENT_TIME', '2025-01-01T00:00:00Z') # Placeholder
            logger.info(f"Tâche #{db_id_to_complete} marquée comme terminée.")
            return jsonify(inventaire)
        else:
            return jsonify({"error": f"Tâche avec l'ID {db_id_to_complete} non trouvée."}), 404
    
    except Exception as e:
        logger.error(f"Erreur lors de la complétion de la tâche: {e}")
        return jsonify({"error": f"Erreur interne: {e}"}), 500

# Ce bloc est utilisé si vous lancez le script directement (non pas via gunicorn)
if __name__ == '__main__':
    # Flask utilise par défaut le port 5000, mais Render utilise 10000.
    # Pour les tests locaux, 5000 est suffisant.
    app.run(debug=True, host='0.0.0.0', port=5000)