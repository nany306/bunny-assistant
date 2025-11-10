# utils/persistence.py
import sqlite3
import os
from typing import List

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistant_data.db")

def get_db_connection():
    """Crée une connexion DB (compatible Flask)."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def initialiser_db():
    """Crée les tables et les index."""
    ddl = """
    CREATE TABLE IF NOT EXISTS evenements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        type_event TEXT NOT NULL,          -- 'Tache' ou 'RDV'
        urgence INTEGER,                   -- Tache
        importance INTEGER,                -- Tache
        duree_totale_minutes INTEGER,      -- Tache
        projet TEXT,                       -- Tache/RDV
        progression_pourcentage INTEGER,   -- Tache
        est_complete INTEGER,              -- Tache (0/1)
        date_heure_debut TEXT,             -- RDV (YYYY-MM-DD HH:MM) ou NULL
        date_limite TEXT,                  -- Tache (YYYY-MM-DD) ou NULL
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_type_complete ON evenements(type_event, est_complete);
    
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        montant REAL NOT NULL,
        type_transaction TEXT NOT NULL, -- 'Dépense' ou 'Revenu'
        categorie TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """
    with get_db_connection() as conn:
        conn.executescript(ddl)

def _import_evenement():
    # import tardif pour éviter les cycles
    from core.evenement import Evenement
    return Evenement

def _row_to_event(row):
    """Convertit une ligne SQL en objet Evenement (dataclass)."""
    Evenement = _import_evenement()
    return Evenement(
        nom=row["nom"],
        type_event=row["type_event"],
        urgence=row["urgence"] or 3,
        importance=row["importance"] or 3,
        duree_totale_minutes=row["duree_totale_minutes"] or 60, # CORRIGÉ
        projet=row["projet"] or "Divers",
        est_complete=bool(row["est_complete"]) if row["est_complete"] is not None else False,
        progression_pourcentage=row["progression_pourcentage"] or 0,
        date_heure_debut=row["date_heure_debut"],
        date_limite=row["date_limite"],
        db_id=row["id"],
        date_creation=row["created_at"]
    )

def charger_inventaire() -> List[object]:
    """Charge tous les événements depuis la DB."""
    initialiser_db()
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM evenements ORDER BY COALESCE(updated_at, created_at), id"
        ).fetchall()
    return [_row_to_event(r) for r in rows]

def sauvegarder_inventaire(liste_evenements) -> None:
    """Sauvegarde (Insert/Update) tous les événements dans la DB."""
    initialiser_db()
    sql_insert = """
        INSERT INTO evenements
        (nom, type_event, urgence, importance, duree_totale_minutes, projet,
         progression_pourcentage, est_complete, date_heure_debut, date_limite, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """
    sql_update = """
        UPDATE evenements SET
            nom=?, type_event=?, urgence=?, importance=?, duree_totale_minutes=?, projet=?,
            progression_pourcentage=?, est_complete=?, date_heure_debut=?, date_limite=?,
            updated_at=datetime('now')
        WHERE id=?
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        for ev in liste_evenements:
            params = (
                ev.nom,
                ev.type_event,
                ev.urgence,
                ev.importance,
                ev.duree_totale_minutes,
                ev.projet,
                ev.progression_pourcentage,
                1 if ev.est_complete else 0,
                ev.date_heure_debut,
                ev.date_limite
            )
            
            if ev.db_id:
                cur.execute(sql_update, (*params, ev.db_id))
            else:
                cur.execute(sql_insert, params)
                setattr(ev, "db_id", cur.lastrowid)
        conn.commit()

# --- Fonctions de Financement ---
# (Nous ajoutons la persistance du financement ici pour centraliser la DB)

def _import_transaction():
    from core.finance_agent import Transaction
    return Transaction

def _row_to_transaction(row):
    Transaction = _import_transaction()
    return Transaction(
        description=row["description"],
        montant=row["montant"],
        type_transaction=row["type_transaction"],
        categorie=row["categorie"],
        date_creation=row["created_at"],
        db_id=row["id"]
    )

def charger_transactions() -> List[object]:
    """Charge toutes les transactions depuis la DB."""
    initialiser_db()
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM transactions ORDER BY created_at").fetchall()
    return [_row_to_transaction(r) for r in rows]

def sauvegarder_transactions(liste_transactions) -> None:
    """Sauvegarde (Insert/Update) toutes les transactions dans la DB."""
    initialiser_db()
    sql_insert = """
        INSERT INTO transactions (description, montant, type_transaction, categorie)
        VALUES (?, ?, ?, ?)
    """
    sql_update = """
        UPDATE transactions SET
            description=?, montant=?, type_transaction=?, categorie=?
        WHERE id=?
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        for tr in liste_transactions:
            params = (tr.description, tr.montant, tr.type_transaction, tr.categorie)
            
            if tr.db_id:
                cur.execute(sql_update, (*params, tr.db_id))
            else:
                cur.execute(sql_insert, params)
                setattr(tr, "db_id", cur.lastrowid)
        conn.commit()