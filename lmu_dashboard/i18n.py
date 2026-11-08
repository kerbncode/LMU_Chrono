"""Langue de l'interface (français / anglais) : textes produits côté Python.

Concerne ce que l'utilisateur voit hors de la page : menu de l'icône près de l'horloge, notifications, fenêtres de
message, messages de mise à jour affichés dans la page, page d'attente. Les textes de la page elle-même sont dans
web_template.html (objet I18N). Les deux dictionnaires doivent rester alignés : tout nouveau texte visible se
traduit dans les deux langues.

Langue : réglage « language » de settings.json (choisi par les drapeaux de la roue crantée) ; à défaut, celle de
Windows (français si l'interface de Windows est en français, anglais sinon).
"""
import ctypes

from . import config

LANGUAGES = ("fr", "en")
LANG_ID_FRENCH = 0x0C   # identifiant de langue principal de Windows

STRINGS = {
    "fr": {
        # Menu de l'icône près de l'horloge et notifications
        "tray_open": "Ouvrir le tableau de bord",
        "tray_refresh": "Actualiser les données",
        "tray_data_folder": "Ouvrir le dossier des données",
        "tray_quit": "Quitter",
        "tray_updating": "mise à jour…",
        "tray_up_to_date": "Données à jour",
        "tray_update_failed": "Échec de la mise à jour : détails dans {log}",
        # Fenêtres de message
        "box_update_failed": "La mise à jour des données a échoué.\nDétails : {log}",
        "box_error": "Une erreur est survenue.\nDétails : {log}",
        # Messages d'actualisation (affichés dans la page)
        "msg_new_files": "{files} nouveau(x) fichier(s), {sessions} session(s) ajoutée(s)",
        "msg_ref_updated": "{count} temps de référence mis à jour",
        "msg_ref_failed": "Google Sheets inaccessible, temps de référence inchangés",
        # Réglages, désinstallation
        "settings_saved": "Réglages enregistrés : résultats relus pour {player}.",
        "no_driver": "aucun pilote trouvé",
        "bad_game_dir": "Ce dossier n'est pas celui de Le Mans Ultimate (UserData\\Log\\Results introuvable). "
                        "Choisissez le dossier « Le Mans Ultimate », dans steamapps\\common.",
        "browse_title": "Dossier de Le Mans Ultimate (…\\steamapps\\common\\Le Mans Ultimate)",
        "uninstalled": "{app} a été désinstallé.",
        "uninstall_exe_only": "La désinstallation n'est disponible que pour l'exécutable.",
        "uninstall_failed": "Désinstallation impossible ({error}).",
        "shortcut_description": "Vos meilleurs temps sur Le Mans Ultimate",
        "wait_page": "Préparation du tableau de bord…",
    },
    "en": {
        "tray_open": "Open the dashboard",
        "tray_refresh": "Refresh data",
        "tray_data_folder": "Open the data folder",
        "tray_quit": "Quit",
        "tray_updating": "updating…",
        "tray_up_to_date": "Data up to date",
        "tray_update_failed": "Update failed: details in {log}",
        "box_update_failed": "The data update failed.\nDetails: {log}",
        "box_error": "An error occurred.\nDetails: {log}",
        "msg_new_files": "{files} new file(s), {sessions} session(s) added",
        "msg_ref_updated": "{count} reference time(s) updated",
        "msg_ref_failed": "Google Sheets unreachable, reference times unchanged",
        "settings_saved": "Settings saved: results re-read for {player}.",
        "no_driver": "no driver found",
        "bad_game_dir": "This folder is not the Le Mans Ultimate folder (UserData\\Log\\Results not found). "
                        "Choose the “Le Mans Ultimate” folder, inside steamapps\\common.",
        "browse_title": "Le Mans Ultimate folder (…\\steamapps\\common\\Le Mans Ultimate)",
        "uninstalled": "{app} has been uninstalled.",
        "uninstall_exe_only": "Uninstalling is only available for the executable.",
        "uninstall_failed": "Cannot uninstall ({error}).",
        "shortcut_description": "Your best times on Le Mans Ultimate",
        "wait_page": "Preparing the dashboard…",
    },
}


def system_language():
    """Langue de l'interface de Windows : « fr » si elle est en français, « en » sinon."""
    try:
        return "fr" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == LANG_ID_FRENCH else "en"
    except (AttributeError, OSError):
        return "en"


def language():
    """Langue en vigueur : réglage de l'utilisateur, sinon langue de Windows."""
    chosen = config.SETTINGS.get("language")
    return chosen if chosen in LANGUAGES else system_language()


def t(key, **params):
    """Texte de l'interface dans la langue en vigueur ; {param} est remplacé par les valeurs passées."""
    return STRINGS[language()][key].format(**params)
