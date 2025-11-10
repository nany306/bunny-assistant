# core/finance_agent.py
from dataclasses import dataclass, field
from datetime import datetime

# Cache global
LISTE_TRANSACTIONS = [] 

@dataclass
class Transaction:
    """Représente une dépense ou un revenu dans un budget."""
    description: str
    montant: float
    type_transaction: str = 'Dépense'
    categorie: str = 'Autre'
    
    date_creation: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    db_id: int = field(default=None)

    def __post_init__(self):
        self.type_transaction = self.type_transaction.capitalize()

    def to_dict(self):
        return {
            "description": self.description,
            "montant": self.montant,
            "type_transaction": self.type_transaction,
            "categorie": self.categorie,
            "date_creation": self.date_creation,
            "db_id": self.db_id
        }