# core/logique.py
from .evenement import Evenement, LISTE_EVENEMENTS_INVENTAIRE

def suggerer_tache(liste_evenements, duree_creneau_minutes):
    """
    Identifie la tâche la plus prioritaire, non terminée, dont le temps restant 
    peut être complété dans la durée du créneau spécifié. Retourne le top 3.
    """
    taches_candidates = [e for e in liste_evenements if e.type_event == "Tache" and not e.est_complete]
    
    # Filtre
    taches_filtrees = [
        t for t in taches_candidates
        if 0 < t.get_duree_restante_minutes() <= duree_creneau_minutes
    ]
    
    # Calcul des scores
    taches_avec_score = [{"tache": t, "score": t.calculer_score_priorite()} for t in taches_filtrees]
    
    # Tri et retour du Top 3
    suggestions = sorted(taches_avec_score, key=lambda x: x["score"], reverse=True)
    return suggestions[:3]