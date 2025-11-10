# core/code_agent.py
import os
from colorama import Fore, Style
import datetime

REQUIREMENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "..", "requirements.txt")

def lire_dependances(fichier=REQUIREMENTS_FILE):
    try:
        with open(fichier, 'r') as f:
            dependances = [ligne.strip() for ligne in f if ligne.strip() and not ligne.startswith('#')]
        return dependances
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur de lecture : {e}{Style.RESET_ALL}")
        return []

def ajouter_dependance(nouvelle_dependance, fichier=REQUIREMENTS_FILE):
    nouvelle_dependance = nouvelle_dependance.strip()
    dependances_existantes = lire_dependances(fichier)
    
    if nouvelle_dependance in dependances_existantes:
        print(f"{Fore.YELLOW}ℹ️ '{nouvelle_dependance}' est déjà dans la liste.{Style.RESET_ALL}")
        return
        
    try:
        with open(fichier, 'a') as f:
            f.write(f"\n{nouvelle_dependance}")
        print(f"{Fore.GREEN}✅ Dépendance '{nouvelle_dependance}' ajoutée.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur d'écriture : {e}{Style.RESET_ALL}")

def generer_et_sauvegarder_code(type_code, nom_fichier, nom_entite):
    nom_fichier_complet = f"{nom_fichier}.py"
    chemin_sauvegarde = os.path.join(os.path.dirname(os.path.abspath(__file__)), nom_fichier_complet)
    
    if type_code.lower() == 'classe':
        contenu = f"""# {nom_entite}.py
# Généré par l'Assistant IA le {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
from dataclasses import dataclass

@dataclass
class {nom_entite}:
    \"\"\" Squelette généré automatiquement. \"\"\"
    
    def __init__(self, *args, **kwargs):
        pass
"""
    else:
        contenu = f"# Squelette de fonction {nom_entite}..."

    try:
        with open(chemin_sauvegarde, 'w') as f:
            f.write(contenu)
        print(f"{Fore.GREEN}✅ Squelette de '{type_code}' généré : {chemin_sauvegarde}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur de sauvegarde : {e}{Style.RESET_ALL}")

def analyser_fichier_source(nom_fichier_py):
    chemin_fichier = os.path.join(os.path.dirname(os.path.abspath(__file__)), nom_fichier_py)
    
    if not os.path.exists(chemin_fichier):
        print(f"{Fore.RED}❌ Fichier introuvable : {chemin_fichier}{Style.RESET_ALL}")
        return None
    try:
        with open(chemin_fichier, 'r') as f:
            lignes = f.readlines()
        return len(lignes)
    except Exception as e:
        print(f"{Fore.RED}❌ Erreur de lecture : {e}{Style.RESET_ALL}")
        return None