# core/evenement.py
from dataclasses import dataclass, field
from datetime import datetime
from marshmallow import Schema, fields, post_load

# LISTE_EVENEMENTS_INVENTAIRE n'est plus utilisé dans cette architecture
# La mémoire est gérée par le client (mobile)

@dataclass
class Evenement:
    """Représente une tâche ou un événement dans l'inventaire."""
    nom: str
    type_event: str = field(default='Tache') # 'Tache', 'Projet', 'RendezVous'
    urgence: int = field(default=3) # 1 (Basse) à 5 (Haute)
    importance: int = field(default=3) # 1 (Faible) à 5 (Forte)
    duree_totale_minutes: int = field(default=60)
    date_creation: datetime = field(default_factory=datetime.now)
    est_complete: bool = field(default=False)
    db_id: int = field(default_factory=lambda: Evenement.generate_id()) # ID unique pour le client
    projet: str = field(default='Divers')
    
    # Stockage de l'ID maximal généré pour garantir l'unicité
    _max_id: int = 0

    @staticmethod
    def generate_id():
        """Génère un ID unique pour cette instance. Nécessite que le client gère le max_id."""
        Evenement._max_id += 1
        return Evenement._max_id

    def marquer_terminee(self):
        self.est_complete = True
        
    def calculer_score_priorite(self):
        """Calcul simple de priorité: (Urgence * Importance) / Durée ajustée"""
        # Ponderation pour que la durée n'écrase pas le score
        duree_ajustee = max(15, self.duree_totale_minutes) # Min 15 min
        score = (self.urgence * self.importance * 10) / (duree_ajustee / 60)
        return score

# --- DÉFINITION DU SCHÉMA MARSHMALLOW (CORRECTION DE L'IMPORTEUR) ---
class EvenementSchema(Schema):
    """Schéma pour sérialiser/désérialiser les objets Evenement via JSON."""
    nom = fields.Str(required=True)
    type_event = fields.Str()
    urgence = fields.Int()
    importance = fields.Int()
    duree_totale_minutes = fields.Int()
    date_creation = fields.DateTime(format='iso')
    est_complete = fields.Bool()
    db_id = fields.Int()
    projet = fields.Str()

    @post_load
    def make_evenement(self, data, **kwargs):
        """Recrée l'objet Evenement après la désérialisation."""
        return Evenement(**data)