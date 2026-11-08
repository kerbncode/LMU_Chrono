"""Serveur local de la page : la sert, et exécute ce que demandent ses boutons (actualisation, réglages,
désinstallation)."""
import json
import os
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import config, data, i18n, install
from .i18n import t
from .pipeline import refresh
from .winutil import browse_folder

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/"
# Arrêt du programme après une désinstallation (posé par le mode icône près de l'horloge)
on_quit = None


def wait_page():
    """Page d'attente, le temps de la toute première génération de la page."""
    return ("<!doctype html><meta charset='utf-8'><meta http-equiv='refresh' content='2'><title>LMU Chrono</title>"
            "<body style='background:#0c0d11;color:#b4b8c5;font:16px system-ui;display:grid;place-items:center;"
            f"height:90vh'>{t('wait_page')}</body>").encode("utf-8")


def settings_json():
    """Réglages pour la fenêtre de la roue crantée : valeur choisie (vide = automatique) et valeur détectée."""
    return {
        "player_name": config.SETTINGS.get("player_name", ""),
        "player_detected": data.detect_player_name() or "",
        "game_dir": config.SETTINGS.get("game_dir", ""),
        "game_detected": config.DETECTED_GAME_DIR or "",
        "can_uninstall": config.FROZEN,
    }


def save_settings(body):
    """Enregistre le nom et le dossier du jeu, puis relit tous les résultats (le joueur ou les fichiers changent)."""
    player = (body.get("player_name") or "").strip()
    game_dir = os.path.normpath(body["game_dir"].strip()) if (body.get("game_dir") or "").strip() else ""
    if game_dir and not config.is_game_dir(game_dir):
        raise ValueError(t("bad_game_dir"))
    config.save_settings(player_name=player, game_dir=game_dir)
    data.detect_player_name.cache_clear()
    refresh(sync_xml=True, rebuild=True)
    return t("settings_saved", player=data.player_name() or t("no_driver"))


def save_language(body):
    """Enregistre la langue choisie (drapeaux de la roue crantée) et régénère la page dans cette langue : la page se
    traduit tout de suite côté navigateur, mais le fichier sur disque (rechargement, mode fichier) doit suivre."""
    language = body.get("language")
    if language not in i18n.LANGUAGES:
        raise ValueError(f"language: {language!r}")
    config.save_settings(language=language)
    refresh(sync_xml=False)


class DashboardHandler(BaseHTTPRequestHandler):
    """GET / : la page générée ; GET /api/settings : réglages ; POST /api/… : actions des boutons de la page."""

    def do_GET(self):
        if self.path == "/api/settings":
            self._send_json(settings_json())
        elif self.path in ("/", "/index.html"):
            if not os.path.exists(config.WEB_OUTPUT):
                self._send(200, "text/html; charset=utf-8", wait_page())
                return
            with open(config.WEB_OUTPUT, "rb") as f:
                self._send(200, "text/html; charset=utf-8", f.read())
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        try:
            if self.path == "/api/refresh-xml":
                result = {"message": refresh(sync_xml=True)}
            elif self.path == "/api/settings":
                result = {"message": save_settings(body)}
            elif self.path == "/api/language":
                save_language(body)
                result = {}
            elif self.path == "/api/browse-game-dir":
                result = {"path": browse_folder(t("browse_title"), body.get("initial") or config.GAME_DIR)}
            elif self.path == "/api/uninstall":
                install.uninstall()
                result = {"message": t("uninstalled", app=config.APP_NAME)}
                if on_quit:
                    threading.Timer(1, on_quit).start()   # après l'envoi de la réponse
            else:
                self.send_error(404)
                return
            self._send_json({"ok": True, **result})
        except Exception as e:
            self._send_json({"ok": False, "message": str(e)})

    def _send_json(self, obj):
        self._send(200, "application/json; charset=utf-8", json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # pas de log pour chaque requête


class ExclusiveHTTPServer(HTTPServer):
    """Port réservé en exclusivité. Par défaut, HTTPServer active SO_REUSEADDR, qui sous Windows laisse un deuxième
    programme ouvrir le même port : un deuxième lancement démarrait alors une deuxième instance au lieu de s'arrêter."""
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):   # Windows
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def create_server():
    """Serveur sur 127.0.0.1 (la page n'est pas accessible depuis le réseau), ou None si le port est déjà pris :
    le tableau de bord tourne alors déjà (lancé une deuxième fois)."""
    try:
        return ExclusiveHTTPServer(("127.0.0.1", PORT), DashboardHandler)
    except OSError:
        return None


def serve(open_browser):
    """Mode console (python lmu.py --serve) : sert la page jusqu'à Ctrl+C ou la fermeture de la fenêtre."""
    server = create_server()
    if server is None:
        print(f"ℹ️ Le tableau de bord est déjà lancé : {URL}")
        webbrowser.open(URL)
        return
    print(f"🌐 Tableau de bord : {URL}")
    print("   Laissez cette fenêtre ouverte pendant l'utilisation ; la fermer arrête le tableau de bord.")
    if open_browser:
        webbrowser.open(URL)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
