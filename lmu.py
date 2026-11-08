"""LMU Chrono — point d'entrée : met à jour la base puis génère la page web.

Usage (code source) :
  python lmu.py              -> analyse les nouveaux XML, génère la page web
  python lmu.py --aliens     -> idem + re-télécharge les temps de référence du Google Sheets
  python lmu.py --rebuild    -> vide la base des tours et relit tous les XML
  python lmu.py --open       -> ouvre la page web (fichier) à la fin
  python lmu.py --serve      -> sert la page sur http://127.0.0.1:8765 avec actualisation et réglages actifs (console)
  python lmu.py --tray       -> comme l'exécutable : icône près de l'horloge, sans console
  python lmu.py --all-tracks -> (LMU lancé) récupère les tracés de tous les circuits du jeu, sans rien générer
  python lmu.py --shortcut   -> (re)crée le raccourci sur le bureau

L'exécutable lancé sans option (double-clic) équivaut à --tray.
"""
import argparse
import os
import sys
import traceback
import webbrowser
from datetime import datetime

from lmu_dashboard import config, install, server, trackmaps
from lmu_dashboard.pipeline import refresh


def main():
    parser = argparse.ArgumentParser(description=f"{config.APP_NAME} : meilleurs temps Le Mans Ultimate")
    parser.add_argument("--aliens", action="store_true", help="mettre à jour les temps de référence depuis le Google Sheets")
    parser.add_argument("--rebuild", action="store_true", help="relire tous les XML depuis zéro")
    parser.add_argument("--open", action="store_true", help="ouvrir la page web à la fin")
    parser.add_argument("--serve", action="store_true", help="servir la page en local (actualisation, réglages)")
    parser.add_argument("--tray", action="store_true", help="icône près de l'horloge, sans console (comme l'exécutable)")
    parser.add_argument("--all-tracks", action="store_true", help="récupérer les tracés de tous les circuits (LMU lancé)")
    parser.add_argument("--shortcut", action="store_true", help="(re)créer le raccourci sur le bureau")
    args = parser.parse_args()

    if args.all_tracks:
        trackmaps.fetch_all()
        return
    if args.tray or (config.FROZEN and not any(vars(args).values())):
        # Même si le jeu est introuvable : la page invite alors à indiquer son dossier dans les réglages
        from lmu_dashboard import tray   # pystray n'est chargé que dans ce mode
        tray.run()
        return
    if not config.is_game_dir(config.GAME_DIR):
        print("❌ Le Mans Ultimate est introuvable dans les bibliothèques Steam : indiquez son dossier dans "
              f"{config.SETTINGS_FILE}, par exemple :\n"
              '   {"game_dir": "D:\\\\SteamLibrary\\\\steamapps\\\\common\\\\Le Mans Ultimate"}')
        return

    refresh(update_ref=args.aliens, rebuild=args.rebuild)
    if args.shortcut:
        install.create_shortcut()
    if args.serve:
        server.serve(open_browser=args.open)
    elif args.open:
        webbrowser.open(f"file:///{config.WEB_OUTPUT.replace(os.sep, '/')}")


if __name__ == "__main__":
    if sys.stdout is None:
        # Sans console (exécutable, pythonw) : les messages vont dans un journal, dans le dossier des données,
        # complété à chaque lancement (remis à zéro au-delà de 1 Mo)
        too_big = os.path.exists(config.LOG_FILE) and os.path.getsize(config.LOG_FILE) > 1_000_000
        sys.stdout = sys.stderr = open(config.LOG_FILE, "w" if too_big else "a", encoding="utf-8", buffering=1)
        print(f"\n--- {datetime.now():%d/%m/%Y %H:%M:%S} ---")
    else:
        # Console Windows ancienne ou sortie redirigée : un caractère non affichable (emoji) ne doit pas faire planter
        for stream in (sys.stdout, sys.stderr):
            stream.reconfigure(errors="replace")
    try:
        main()
    except Exception:
        traceback.print_exc()
        if config.FROZEN:
            from lmu_dashboard.i18n import t
            from lmu_dashboard.winutil import message_box
            message_box(t("box_error", log=config.LOG_FILE), error=True)
        else:
            raise
