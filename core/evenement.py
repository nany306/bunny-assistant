# core/evenement.py
from dataclasses import dataclass, field
from datetime import datetime
from marshmallow import Schema, fields, post_load

# Générateur d'ID unique (solution simple pour le stateless)
_max_id_counter = int(datetime.now().timestamp())

def generate_unique_id():
    """Génère un ID unique simple basé sur le timestamp."""
    global _max_id_counter
    _max_id_counter += 1
    return _max_id_counter

@dataclass
class Evenement:
    """Représente une tâche ou un événement dans l'inventaire."""
    nom: str
    type_event: str = field(default='Tache')
    urgence: int = field(default=3)
    importance: int = field(default=3)
    duree_totale_minutes: int = field(default=60)
    projet: str = field(default='Divers')
    est_complete: bool = field(default=False)
    
    # --- MISE À JOUR DU CALENDRIER ---
    # La date de création est remplacée par une date de début
    date_debut: datetime = field(default_factory=datetime.now)
    date_fin: datetime = field(default=None) # Pour les événements sur plusieurs jours
    # ---------------------------------
    
    db_id: int = field(default_factory=generate_unique_id) 

    def marquer_terminee(self):
        self.est_complete = True
        
    def calculer_score_priorite(self):
        """Calcul simple de priorité pour les Tâches."""
        if self.type_event != 'Tache' or self.est_complete:
            return 0
            
        duree_ajustee = max(15, self.duree_totale_minutes) 
        score = (self.urgence * self.importance * 10) / (duree_ajustee / 60)
        
        # Bonus si la date de début est aujourd'hui ou passée (pour les tâches)
        try:
            jours_restants = (self.date_debut.date() - datetime.now().date()).days
            if jours_restants <= 0:
                score *= 1.5 # Augmentation de 50% si c'est pour aujourd'hui
        except Exception:
            pass # Ignorer les erreurs de date
            
        return score

# --- DÉFINITION DU SCHÉMA MARSHMALLOW (Corrigé) ---
class EvenementSchema(Schema):
    """Schéma pour sérialiser/désérialiser les objets Evenement via JSON."""
    nom = fields.Str(required=True)
    type_event = fields.Str()
    urgence = fields.Int()
    importance = fields.Int()
    duree_totale_minutes = fields.Int()
    projet = fields.Str()
    est_complete = fields.Bool()
    
    # --- MISE À JOUR DU CALENDRIER ---
    # On utilise le format ISO (YYYY-MM-DDTHH:MM:SS)
    date_debut = fields.DateTime(format='iso', allow_none=True)
    date_fin = fields.DateTime(format='iso', allow_none=True) 
    # ---------------------------------
    
    db_id = fields.Int()

    @post_load
    def make_evenement(self, data, **kwargs):
        """Recrée l'objet Evenement après la désérialisation."""
        return Evenement(**data)