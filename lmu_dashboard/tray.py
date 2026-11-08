"""Mode « icône près de l'horloge » (double-clic sur l'exécutable) : aucune fenêtre, une icône dans la zone de
notification de Windows, avec un menu pour ouvrir le tableau de bord, actualiser les données ou quitter."""
import os
import threading
import traceback
import webbrowser

import pystray
from PIL import Image

from . import config, install, server
from .i18n import t
from .pipeline import refresh
from .winutil import message_box


def run():
    httpd = server.create_server()
    if httpd is None:   # déjà lancé : on rouvre simplement la page
        webbrowser.open(server.URL)
        return
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def open_dashboard(icon=None, item=None):
        webbrowser.open(server.URL)

    def update(icon, notify_result):
        icon.title = f"{config.APP_NAME} · {t('tray_updating')}"
        try:
            message = refresh(sync_xml=True)
            if notify_result:
                icon.notify(message or t("tray_up_to_date"), config.APP_NAME)
        except Exception:
            traceback.print_exc()
            icon.notify(t("tray_update_failed", log=config.LOG_FILE), config.APP_NAME)
        icon.title = config.APP_NAME

    def refresh_clicked(icon, item):
        threading.Thread(target=update, args=(icon, True), daemon=True).start()

    def startup(icon):
        # Appelée dans un fil à part par pystray : l'icône répond pendant la mise à jour du lancement
        icon.visible = True
        icon.title = f"{config.APP_NAME} · {t('tray_updating')}"
        try:
            refresh(update_ref=True)   # temps de référence remis à jour à chaque lancement
        except Exception:
            traceback.print_exc()
            message_box(t("box_update_failed", log=config.LOG_FILE), error=True)
        icon.title = config.APP_NAME
        install.ensure_shortcut()
        open_dashboard()

    # Textes donnés par des fonctions : le menu suit la langue choisie dans les réglages sans redémarrer
    menu = pystray.Menu(
        pystray.MenuItem(lambda item: t("tray_open"), open_dashboard, default=True),   # aussi au double-clic
        pystray.MenuItem(lambda item: t("tray_refresh"), refresh_clicked),
        pystray.MenuItem(lambda item: t("tray_data_folder"), lambda icon, item: os.startfile(config.DATA_DIR)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda item: t("tray_quit"), lambda icon, item: icon.stop()),
    )
    icon = pystray.Icon("lmu_chrono", Image.open(config.ICON_PNG), config.APP_NAME, menu)
    server.on_quit = icon.stop   # désinstallation demandée depuis la page
    try:
        icon.run(setup=startup)
    finally:
        httpd.shutdown()
        httpd.server_close()
