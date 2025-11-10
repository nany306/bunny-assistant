# core/evenement.py
from dataclasses import dataclass, field
from datetime import datetime

# Cache global pour l'inventaire en mémoire (utilisé par l'API et la CLI)
LISTE_EVENEMENTS_INVENTAIRE = [] 

@dataclass
class Evenement:
    # --- Champs obligatoires pour la logique métier ---
    nom: str
    type_event: str # 'Tache' ou 'RDV'
    
    # --- Champs Tâche (optionnels pour RDV) ---
    urgence: int = 3
    importance: int = 3
    duree_totale_minutes: int = 60
    projet: str = "Divers"
    
    # --- Champs de statut/Progression ---
    progression_pourcentage: int = 0
    est_complete: bool = False
    
    # --- Champs de Date (Utilisation de field pour les valeurs par défaut) ---
    date_creation: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    date_heure_debut: str = None # Pour les RDV
    date_limite: str = None # Pour les Tâches
    
    # --- CLÉ PRIMAIRE POUR LA DB (ESSENTIEL POUR LA PERSISTANCE SQLITE) ---
    db_id: int = field(default=None) 

    # --- MÉTHODES UTILES ---
    
    def get_duree_restante_minutes(self):
        """Calcule le temps restant à partir de la durée totale et de la progression."""
        temps_restant = self.duree_totale_minutes * (1 - (self.progression_pourcentage / 100))
        return max(0, int(temps_restant))

    def calculer_score_priorite(self):
        """Calcule la priorité (Logique simplifiée pour la démo, à adapter)."""
        if self.type_event == 'Tache' and not self.est_complete and self.duree_totale_minutes > 0:
            # Facteur d'urgence/importance
            score = (self.urgence * 1.5) + (self.importance * 1.0)
            
            # Facteur d'échéance (Bonus si proche)
            if self.date_limite:
                try:
                    echeance_date = datetime.strptime(self.date_limite, '%Y-%m-%d').date()
                    jours_restants = (echeance_date - datetime.today().date()).days
                    if jours_restants <= 0:
                        return float('inf') # Priorité absolue
                    if jours_restants < 7:
                        score *= (7 / jours_restants)
                except ValueError:
                    pass # Format de date invalide
                    
            return score
        return 0

    def marquer_terminee(self):
        """Met à jour le statut de l'événement comme terminé."""
        self.progression_pourcentage = 100
        self.est_complete = True
    
    def to_dict(self):
        """Retourne un dictionnaire des attributs pour l'API/sauvegarde."""
        return {
            'nom': self.nom,
            'type_event': self.type_event,
            'urgence': self.urgence,
            'importance': self.importance,
            'duree_minutes': self.duree_totale_minutes, # Nom standardisé pour l'API
            'projet': self.projet,
            'progression_pourcentage': self.progression_pourcentage,
            'est_complete': self.est_complete,
            'date_creation': self.date_creation,
            'date_heure_debut': self.date_heure_debut,
            'date_limite': self.date_limite,
            'db_id': self.db_id,
        }