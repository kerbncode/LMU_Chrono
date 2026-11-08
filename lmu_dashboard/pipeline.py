"""Mise à jour complète : base de données, puis page web."""
import threading

from . import data
from .assets import ensure_assets
from .i18n import t
from .web import export_web

# Une seule mise à jour à la fois (bouton ↻ de la page, réglages, menu de l'icône près de l'horloge)
_lock = threading.Lock()


def refresh(sync_xml=True, update_ref=False, rebuild=False):
    """Met à jour la base et régénère la page. Retourne un message de résumé."""
    with _lock:
        return _refresh(sync_xml, update_ref, rebuild)


def _refresh(sync_xml, update_ref, rebuild):
    messages = []
    with data.connect() as conn:
        if sync_xml:
            new_files, added = data.sync_results(conn, rebuild=rebuild)
            messages.append(t("msg_new_files", files=new_files, sessions=added))
        if update_ref or data.alien_times_count(conn) == 0:
            count = data.update_alien_times(conn)
            messages.append(t("msg_ref_updated", count=count) if count else t("msg_ref_failed"))
        table = data.get_best_table(conn)

    if not any(block["rows"] for block in table):
        print(f"⚠️ Aucun tour trouvé pour '{data.player_name()}'.")
    ensure_assets()
    export_web(table)
    return " · ".join(messages)
