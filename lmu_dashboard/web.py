"""Export de la page web : un fichier HTML autonome (données, images et polices intégrées en data URI)."""
import base64
import json
import os
import re
from datetime import datetime

from . import config, i18n
from . import data as data_module
from .assets import find_asset, slugify
from .data import format_lap_time

TEMPLATE = os.path.join(config.APP_DIR, "lmu_dashboard", "web_template.html")
DISPLAY_DATE = "%H:%M %d/%m/%y"
MIME = {".svg": "image/svg+xml", ".png": "image/png", ".ttf": "font/ttf"}
# Marques les plus longues d'abord ("Mercedes-AMG" avant un éventuel "Mercedes")
BRANDS = sorted(config.BRANDS, key=len, reverse=True)
# Désignation de classe dans le nom de la voiture, avec un éventuel suffixe collé (« LMGT3.R »)
CLASS_TOKENS_RE = re.compile(r"\b(" + "|".join(map(re.escape, config.CLASS_TOKENS)) + r")(\.\w+)?\b", re.IGNORECASE)
# Polices de l'interface du jeu : nom de famille CSS, graisse, fichier (assets/game/fonts)
FONTS = [
    ("LMU Antonio", "normal", "Antonio-SemiBold"),
    ("LMU Heebo", "400", "Heebo-Regular"),
    ("LMU Heebo", "600", "Heebo-SemiBold"),
    ("LMU Heebo", "700", "Heebo-Bold"),
]


class Assets:
    """Fichiers intégrés une seule fois dans la page (data URI), référencés par clé."""

    def __init__(self):
        self.uris = {}

    def ref(self, kind, stem):
        path = stem and find_asset(kind, stem)
        if not path:
            return None
        key = f"{kind}/{os.path.basename(path)}"
        if key not in self.uris:
            with open(path, "rb") as f:
                raw = base64.b64encode(f.read()).decode("ascii")
            self.uris[key] = f"data:{MIME[os.path.splitext(path)[1]]};base64,{raw}"
        return key


def split_car(car_type, assets):
    """'Ferrari 296 LMGT3 Evo' -> marque + logos du jeu (fond sombre / fond clair) + modèle sans la classe ('296 Evo')."""
    brand = next((b for b in BRANDS if car_type.lower().startswith(b.lower())), None)
    rest = car_type[len(brand):] if brand else car_type
    # Sans nom de modèle (« Mercedes-AMG LMGT3 » : il ne reste que la classe), on affiche la marque
    model = re.sub(r"\s{2,}", " ", CLASS_TOKENS_RE.sub("", rest)).strip(" -") or brand or car_type
    logo = brand and assets.ref("game/brands", slugify(brand))
    return {
        "brand": brand,
        "model": model,
        "logo": logo,
        # « Brand=X Dark.svg » du jeu, pour fond clair ; à défaut le logo normal
        "logo_light": logo and (assets.ref("game/brands", slugify(brand) + "_dark") or logo),
    }


def session_json(session, assets):
    if session is None:
        return None
    date = session["date"]
    return {
        "best_lap": session["best_lap"],
        "time": format_lap_time(session["best_lap"]),
        "day": date.strftime("%d/%m/%y") if date else "",
        "hour": date.strftime("%H:%M") if date else "",
        "date_iso": date.isoformat() if date else "",
        "car": session["car_type"],
        # Nouveau record (badge) : ancien temps et gain en secondes
        "record_previous_time": format_lap_time(session["record_previous"]) if session["record_previous"] else None,
        "record_gain": round(session["record_previous"] - session["best_lap"], 3) if session["record_previous"] else None,
        **split_car(session["car_type"], assets),
    }


def export_web(table, path=config.WEB_OUTPUT):
    assets = Assets()

    def row_json(row):
        short_name = config.CIRCUIT_CORRESP.get(row["circuit"])
        track = config.TRACKS.get(short_name, {})
        return {
            "circuit": row["circuit"],
            "short_name": short_name,
            "country": track.get("country"),
            "flag": assets.ref("game/flags", track.get("country")),
            "track_map": assets.ref("game/trackmaps", track.get("scene", "").lower() or None),
            "sessions": row["sessions"],
            "q": session_json(row["qualif"], assets),
            "c": session_json(row["course"], assets),
            "best": row["best"],
            "best_time": format_lap_time(row["best"]),
            "alien": row["alien"],
            "alien_time": format_lap_time(row["alien"]),
            "gap": row["gap"],
        }

    classes = [
        {
            "key": block["class"]["xml"],
            "name": block["class"]["name"],
            "tab": block["class"]["tab"],
            "color": block["class"]["color"],
            "badge": block["class"]["badge"],
            "badge_corner": block["class"].get("badge_corner"),   # triangle en haut à droite (ELMS)
            "rows": [row_json(row) for row in block["rows"]],
        }
        for block in table
    ]
    rows = [row for c in classes for row in c["rows"]]
    # Messages d'aide affichés en haut de la page (premier lancement surtout) : clés traduites par la page
    # (I18N de web_template.html), pour suivre le changement de langue sans régénérer la page
    notices = []
    if not config.is_game_dir(config.GAME_DIR):
        notices.append({"key": "notice_game_missing"})
    elif not rows:
        notices.append({"key": "notice_no_session"})
    missing_maps = {row["circuit"] for row in rows if not row["track_map"]}
    if missing_maps:
        notices.append({"key": "notice_missing_maps", "n": len(missing_maps)})

    data = {
        "language": i18n.language(),
        # Drapeaux du choix de langue (roue crantée) : ceux du jeu, comme pour les circuits (Royaume-Uni pour l'anglais)
        "language_flags": {"fr": assets.ref("game/flags", "fr"), "en": assets.ref("game/flags", "gb")},
        "player": data_module.player_name() or "",
        "generated_at": datetime.now().strftime(DISPLAY_DATE),
        # Page publique du Google Sheets d'Ohne Speed (temps de référence), pour le lien du pied de page
        "sheet_url": config.ALIEN_CSV_URL.replace("pub?output=csv", "pubhtml"),
        "notices": notices,
        "classes": classes,
        "fonts": [{"family": family, "weight": weight, "src": assets.ref("game/fonts", stem)}
                  for family, weight, stem in FONTS],
        "logo": assets.ref("game/logos", "lmu_logo_icon"),
    }
    with open(config.ICON_PNG, "rb") as f:   # icône de l'onglet du navigateur
        data["favicon"] = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    data["assets"] = assets.uris
    _write_page(data, path)


def _write_page(data, path):
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()
    # "</" échappé pour qu'un nom de voiture ne puisse pas fermer la balise <script>
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html.replace("/*__DATA__*/", payload))
    print(f"✅ Page web générée : {path}")
