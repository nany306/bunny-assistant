# interfaces/cli_main.py
import datetime
from colorama import Fore, Style
import sys
import os

# Ajout du répertoire parent au path pour les imports relatifs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import de tous les composants
from core.evenement import Evenement, LISTE_EVENEMENTS_INVENTAIRE
from core.logique import suggerer_tache
from core.code_agent import lire_dependances, ajouter_dependance, generer_et_sauvegarder_code, analyser_fichier_source 
from core.finance_agent import Transaction, LISTE_TRANSACTIONS
from utils.persistence import charger_inventaire, sauvegarder_inventaire, charger_transactions, sauvegarder_transactions

# === FONCTIONS D'INTERACTION ===

def ajouter_evenement_cli(liste_evenements):
    print(f"\n{Fore.BLUE}--- AJOUTER UN NOUVEL ÉVÉNEMENT ---{Style.RESET_ALL}")
    type_event = input("Type (Tache/RDV) : ").strip().capitalize()
    nom = input("Nom de l'événement : ").strip()
    
    if type_event == 'Rdv':
        try:
            date_str = input("Date et heure de début (AAAA-MM-JJ HH:MM) : ").strip()
            duree_minutes = int(input("Durée (en minutes) : "))
            
            nouveau_event = Evenement(nom=nom, type_event='RDV', duree_totale_minutes=duree_minutes, date_heure_debut=date_str)
            liste_evenements.append(nouveau_event)
            print(f"{Fore.GREEN}✅ Rendez-vous '{nom}' ajouté.{Style.RESET_ALL}")
            sauvegarder_inventaire(liste_evenements)
        except ValueError:
            print(f"{Fore.RED}❌ Erreur de format. Annulation.{Style.RESET_ALL}")
    elif type_event == 'Tache':
        try:
            urgence = int(input("Urgence (1-5) : "))
            importance = int(input("Importance (1-5) : "))
            duree_minutes = int(input("Durée estimée (en minutes) : "))
            projet = input("Projet associé : ").strip()
            date_limite = input("Date limite (AAAA-MM-JJ) : ").strip() or None
            
            nouveau_event = Evenement(nom=nom, type_event='Tache', urgence=urgence, importance=importance, duree_totale_minutes=duree_minutes, projet=projet, date_limite=date_limite)
            liste_evenements.append(nouveau_event)
            print(f"{Fore.GREEN}✅ Tâche '{nom}' ajoutée.{Style.RESET_ALL}")
            sauvegarder_inventaire(liste_evenements)
        except ValueError:
            print(f"{Fore.RED}❌ Erreur de format. Annulation.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Type non reconnu.{Style.RESET_ALL}")

def afficher_inventaire_cli(liste_evenements):
    print(f"\n{Fore.CYAN}--- INVENTAIRE COMPLET ({len(liste_evenements)} ÉLÉMENTS) ---{Style.RESET_ALL}")
    
    taches_actives = [e for e in liste_evenements if e.type_event == 'Tache' and not e.est_complete]
    taches_completes = [e for e in liste_evenements if e.type_event == 'Tache' and e.est_complete]
    rdv = [e for e in liste_evenements if e.type_event == 'RDV']
    
    print(f"\n{Fore.MAGENTA}--- TÂCHES ACTIVES (Priorisées) ---{Style.RESET_ALL}")
    taches_actives_triees = sorted(taches_actives, key=lambda x: x.calculer_score_priorite(), reverse=True)
    if taches_actives_triees:
        for t in taches_actives_triees:
            print(f"- (Score {t.calculer_score_priorite():.2f}) {t.nom} [{t.progression_pourcentage}%] (Reste {t.get_duree_restante_minutes()} min)")
    else:
        print(f"  {Fore.YELLOW}Aucune tâche active.{Style.RESET_ALL}")

    print(f"\n{Fore.MAGENTA}--- RENDEZ-VOUS ---{Style.RESET_ALL}")
    if rdv:
        for r in rdv:
            print(f"- {r.nom} (Le {r.date_heure_debut})")
    else:
        print(f"  {Fore.YELLOW}Aucun rendez-vous.{Style.RESET_ALL}")

    print(f"\n{Fore.MAGENTA}--- TÂCHES COMPLÉTÉES ---{Style.RESET_ALL}")
    if taches_completes:
        for t in taches_completes:
            print(f"- {t.nom} (Terminée)")
    else:
        print(f"  {Fore.YELLOW}Aucune tâche complétée.{Style.RESET_ALL}")

def marquer_terminee_cli(liste_evenements):
    taches_actives = [e for e in liste_evenements if e.type_event == 'Tache' and not e.est_complete]
    if not taches_actives:
        print(f"{Fore.YELLOW}Aucune tâche active à terminer.{Style.RESET_ALL}")
        return
    
    for i, tache in enumerate(taches_actives):
        print(f"{i+1}. {tache.nom}")
    try:
        choix = int(input("Numéro de la tâche à terminer (0 pour annuler) : "))
        if 1 <= choix <= len(taches_actives):
            taches_actives[choix - 1].marquer_terminee()
            sauvegarder_inventaire(liste_evenements)
            print(f"{Fore.GREEN}✅ Tâche marquée comme terminée.{Style.RESET_ALL}")
    except ValueError:
        print(f"{Fore.RED}❌ Choix invalide.{Style.RESET_ALL}")

def marquer_progression_cli(liste_evenements):
    taches_actives = [e for e in liste_evenements if e.type_event == 'Tache' and not e.est_complete]
    if not taches_actives:
        print(f"{Fore.YELLOW}Aucune tâche active.{Style.RESET_ALL}")
        return

    for i, tache in enumerate(taches_actives):
        print(f"{i+1}. {tache.nom} ({tache.progression_pourcentage}%)")
    try:
        choix = int(input("Numéro de la tâche à mettre à jour (0 pour annuler) : "))
        if 1 <= choix <= len(taches_actives):
            tache = taches_actives[choix - 1]
            progression = int(input(f"Progression effectuée (en %) pour '{tache.nom}' : "))
            tache.progression_pourcentage = min(100, tache.progression_pourcentage + progression)
            if tache.progression_pourcentage == 100:
                tache.marquer_terminee()
            sauvegarder_inventaire(liste_evenements)
            print(f"{Fore.GREEN}✅ Progression mise à jour.{Style.RESET_ALL}")
    except ValueError:
        print(f"{Fore.RED}❌ Entrée invalide.{Style.RESET_ALL}")

def gerer_finance_ajout_cli(liste_transactions):
    print(f"\n{Fore.BLUE}--- AJOUTER UNE TRANSACTION ---{Style.RESET_ALL}")
    try:
        description = input("Description : ").strip()
        montant = float(input("Montant (ex: 50.00) : "))
        type_transaction = input("Type (Dépense/Revenu) : ").strip().capitalize()
        categorie = input("Catégorie : ").strip()
        
        if description and montant != 0 and type_transaction in ['Dépense', 'Revenu']:
            nouvelle_tr = Transaction(description, montant, type_transaction, categorie)
            liste_transactions.append(nouvelle_tr)
            sauvegarder_transactions(liste_transactions)
            print(f"{Fore.GREEN}✅ Transaction ajoutée.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Informations invalides.{Style.RESET_ALL}")
    except ValueError:
        print(f"{Fore.RED}❌ Le montant doit être un nombre.{Style.RESET_ALL}")

def afficher_bilan_finance_cli(liste_transactions):
    print(f"\n{Fore.CYAN}--- BILAN FINANCIER ---{Style.RESET_ALL}")
    total_revenu = sum(t.montant for t in liste_transactions if t.type_transaction == 'Revenu')
    total_depense = sum(t.montant for t in liste_transactions if t.type_transaction == 'Dépense')
    solde_net = total_revenu - total_depense
    
    couleur_solde = Fore.GREEN if solde_net >= 0 else Fore.RED
    print(f"💰 Total Revenu : {Fore.GREEN}{total_revenu:.2f}€{Style.RESET_ALL}")
    print(f"💸 Total Dépense : {Fore.RED}{total_depense:.2f}€{Style.RESET_ALL}")
    print(f"Net Solde Actuel : {couleur_solde}{solde_net:.2f}€{Style.RESET_ALL}")
    
    print(f"\n{Fore.MAGENTA}--- Dernières Transactions ---{Style.RESET_ALL}")
    if liste_transactions:
        for t in reversed(liste_transactions[-5:]):
            signe = Fore.RED + "-" if t.type_transaction == 'Dépense' else Fore.GREEN + "+"
            print(f"- [{signe}{t.montant:.2f}€{Style.RESET_ALL}] {t.description} ({t.categorie})")
    else:
        print(f"  {Fore.YELLOW}Aucune transaction.{Style.RESET_ALL}")


def main_menu():
    global LISTE_EVENEMENTS_INVENTAIRE, LISTE_TRANSACTIONS
    
    LISTE_EVENEMENTS_INVENTAIRE = charger_inventaire()
    LISTE_TRANSACTIONS = charger_transactions()
    
    print(f"{Fore.GREEN}✅ {len(LISTE_EVENEMENTS_INVENTAIRE)} événements et {len(LISTE_TRANSACTIONS)} transactions chargés.{Style.RESET_ALL}")
    
    # Logique de démo si DB vide (optionnel)
    if not LISTE_EVENEMENTS_INVENTAIRE:
        print(f"{Fore.YELLOW}Création des données de démo...{Style.RESET_ALL}")
        LISTE_EVENEMENTS_INVENTAIRE.append(Evenement(nom="Vérifier contrat A", type_event='Tache', urgence=5, importance=5, duree_totale_minutes=120, projet="Financement", date_limite="2025-11-15"))
        LISTE_EVENEMENTS_INVENTAIRE.append(Evenement(nom="Finaliser le rapport", type_event='Tache', urgence=4, importance=4, duree_totale_minutes=60, projet="Gestion", date_limite="2025-11-10"))
        sauvegarder_inventaire(LISTE_EVENEMENTS_INVENTAIRE)
    if not LISTE_TRANSACTIONS:
        LISTE_TRANSACTIONS.append(Transaction("Salaire", 3000, "Revenu", "Salaire"))
        sauvegarder_transactions(LISTE_TRANSACTIONS)
    
    while True:
        print(f"\n{Fore.CYAN}=== ASSISTANT PERSONNEL IA (CLI) ==={Style.RESET_ALL}")
        print("1. Afficher l'inventaire complet")
        print("2. Ajouter un nouvel événement (Tâche ou RDV)")
        print("3. Suggérer la meilleure tâche pour un créneau libre")
        print("4. Marquer une tâche comme terminée")
        print("5. Mettre à jour la progression d'une tâche")
        print(f"\n{Fore.MAGENTA}--- DOMAINE CODE ---{Style.RESET_ALL}")
        print("7. Afficher les dépendances")
        print("8. Ajouter une dépendance")
        print("9. Générer squelette de code")
        print("10. Analyser Fichier Source")
        print(f"\n{Fore.YELLOW}--- DOMAINE FINANCEMENT ---{Style.RESET_ALL}")
        print("11. Afficher Bilan Financier")
        print("12. Ajouter une Transaction")
        print(f"\n{Fore.RED}6. Quitter{Style.RESET_ALL}")
        
        choix = input("Entrez votre choix (1-12) : ").strip()
        
        if choix == '1':
            afficher_inventaire_cli(LISTE_EVENEMENTS_INVENTAIRE)
        elif choix == '2':
            ajouter_evenement_cli(LISTE_EVENEMENTS_INVENTAIRE)
        elif choix == '3':
            try:
                duree = int(input("Durée du créneau libre (en minutes) : "))
                suggestions = suggerer_tache(LISTE_EVENEMENTS_INVENTAIRE, duree)
                if suggestions:
                    print(f"{Fore.GREEN}✅ TOP SUGGESTIONS :{Style.RESET_ALL}")
                    for s in suggestions:
                        print(f"   - {s['tache'].nom} (Score: {s['score']:.2f})")
                else:
                    print(f"{Fore.YELLOW}Aucune tâche ne correspond.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}❌ Durée invalide.{Style.RESET_ALL}")
        elif choix == '4':
            marquer_terminee_cli(LISTE_EVENEMENTS_INVENTAIRE)
        elif choix == '5':
            marquer_progression_cli(LISTE_EVENEMENTS_INVENTAIRE)
        elif choix == '7':
            print(lire_dependances())
        elif choix == '8':
            dep = input("Nom du package à ajouter : ")
            ajouter_dependance(dep)
        elif choix == '9': 
            tc = input("Type (Classe/Fonction) : ")
            nf = input("Nom fichier (sans .py) : ")
            ne = input("Nom entité : ")
            generer_et_sauvegarder_code(tc, nf, ne)
        elif choix == '10': 
            nf = input("Nom fichier (ex: evenement.py) : ")
            lignes = analyser_fichier_source(nf)
            if lignes is not None:
                print(f"Le fichier contient {lignes} lignes.")
        
        elif choix == '11':
            afficher_bilan_finance_cli(LISTE_TRANSACTIONS)
        elif choix == '12':
            gerer_finance_ajout_cli(LISTE_TRANSACTIONS)
            
        elif choix == '6':
            print(f"{Fore.GREEN}Au revoir !{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Choix invalide.{Style.RESET_ALL}")

if __name__ == "__main__":
    main_menu()