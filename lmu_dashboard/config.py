"""Configuration et chemins.

  config.json   : configuration partagée (classes, circuits, marques…), livrée avec le programme
  settings.json : réglages personnels, dans le dossier des données ({"player_name": …, "game_dir": …}), modifiables
                  depuis la page (roue crantée) ; sans eux, le joueur et le dossier du jeu sont détectés automatiquement

Dossier des données (base, page web, images extraites du jeu, journal) : le dossier du projet quand on lance le code
source, « %LOCALAPPDATA%\\LMU Chrono » pour l'exécutable (ni synchronisé par OneDrive, ni concerné par la protection
des dossiers de Windows Defender, contrairement à Documents).
"""
import json
import os
import sys

from . import steam

APP_NAME = "LMU Chrono"
FROZEN = getattr(sys, "frozen", False)   # exécutable PyInstaller
# Fichiers livrés avec le programme (config.json, gabarit de la page, icône) : dans l'exécutable, ou à la racine du projet
APP_DIR = sys._MEIPASS if FROZEN else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(APP_DIR, "lmu_dashboard", "resources")
ICON_ICO = os.path.join(RESOURCES_DIR, "icon.ico")   # exécutable, raccourci
ICON_PNG = os.path.join(RESOURCES_DIR, "icon.png")   # icône près de l'horloge, onglet du navigateur

_local_appdata = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
DATA_DIR = os.path.join(_local_appdata, APP_NAME) if FROZEN else APP_DIR
os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(APP_DIR, "config.json"), "r", encoding="utf-8") as f:
    _config = json.load(f)

LOG_FILE = os.path.join(DATA_DIR, "lmu-chrono.log")   # messages des lancements sans fenêtre
DB_FILE = os.path.join(DATA_DIR, "lmu.db")
WEB_OUTPUT = os.path.join(DATA_DIR, "Meilleurs_Temps_LMU.html")
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
ALIEN_CSV_URL = _config["alien_sheet_csv_url"]

CLASSES = _config["classes"]
CIRCUIT_CORRESP = _config["circuit_corresp_alien"]
TRACKS = _config["tracks"]
BRANDS = _config["brands"]
CLASS_TOKENS = _config["class_tokens"]

# --- Réglages personnels (settings.json) ---

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
SETTINGS = {}
if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        SETTINGS = json.load(f)

DETECTED_GAME_DIR = steam.find_game_dir()   # recherche dans les bibliothèques Steam (None si introuvable)
GAME_DIR = RESULTS_DIR = UI_ZIP = None


def _apply_settings():
    """Dossier du jeu : réglage "game_dir", sinon celui trouvé dans Steam. Les autres modules lisent config.GAME_DIR,
    config.RESULTS_DIR… au moment de s'en servir : un changement de réglage est pris en compte sans relancer."""
    global GAME_DIR, RESULTS_DIR, UI_ZIP
    GAME_DIR = SETTINGS.get("game_dir") or DETECTED_GAME_DIR
    RESULTS_DIR = GAME_DIR and os.path.join(GAME_DIR, "UserData", "Log", "Results")
    UI_ZIP = GAME_DIR and os.path.join(GAME_DIR, "Bin", "UI.zip")


def is_game_dir(path):
    return bool(path) and os.path.isdir(os.path.join(path, "UserData", "Log", "Results"))


def save_settings(**changes):
    """Enregistre des réglages ; une valeur vide les retire (retour à la détection automatique)."""
    for key, value in changes.items():
        if value:
            SETTINGS[key] = value
        else:
            SETTINGS.pop(key, None)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
    _apply_settings()


_apply_settings()
