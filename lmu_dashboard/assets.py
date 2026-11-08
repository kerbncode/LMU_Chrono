"""Images et polices de la page web, dans assets/game/ (seuls les fichiers manquants sont récupérés).

Tout vient de l'installation du joueur, jamais redistribué :
Depuis Bin\\UI.zip (l'interface HTML de LMU) :
  - brands/<marque>.svg (+ _dark.svg) : logos officiels des marques (version fond sombre / fond clair)
  - flags/<pays>.svg                  : drapeaux des pays des circuits (flag-icons, embarqué par le jeu)
  - fonts/*.ttf                       : polices de l'interface (Antonio, Heebo)
  - logos/lmu_logo_icon.png           : monogramme « LM » du bandeau
Depuis l'API locale du jeu (LMU lancé) :
  - trackmaps/<scene>.svg             : tracés des circuits (voir trackmaps.py)
"""
import os
import re
import zipfile

from . import config, trackmaps

FONTS = ("Antonio-SemiBold", "Heebo-Regular", "Heebo-SemiBold", "Heebo-Bold")
GAME_ASSETS = os.path.join(config.ASSETS_DIR, "game")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def find_asset(kind, stem):
    """Chemin du fichier assets/<kind>/<stem>.svg|.png|.ttf s'il existe, sinon None."""
    for ext in (".svg", ".png", ".ttf"):
        path = os.path.join(config.ASSETS_DIR, kind, stem + ext)
        if os.path.exists(path):
            return path
    return None


def _hashed(names, stem, ext, accept=lambda name: True):
    """Fichier start/assets/<stem>-<empreinte><ext> : l'empreinte (8 caractères) change avec les versions du jeu."""
    pattern = re.compile(rf"start/assets/{re.escape(stem)}-[A-Za-z0-9_-]{{8}}{re.escape(ext)}")
    return next((n for n in sorted(names) if pattern.fullmatch(n) and accept(n)), None)


def extract_game_assets():
    """Copie depuis Bin\\UI.zip les logos de marques, drapeaux, polices et logo LMU, s'ils manquent."""
    wanted = {}   # nom dans UI.zip -> fichier local
    hashed = {}   # fichiers dont le nom dans UI.zip porte une empreinte, cherchés dans l'archive -> fichier local
    for brand in config.BRANDS:
        # "Brand=X.svg" est prévu pour un fond sombre, "Brand=X Dark.svg" pour un fond clair
        for variant, suffix in (("", ""), (" Dark", "_dark")):
            wanted[f"start/images/manufacturer/Brand={brand}{variant}.svg"] = \
                os.path.join(GAME_ASSETS, "brands", slugify(brand) + suffix + ".svg")
    for font in FONTS:
        wanted[f"start/fonts/{font}.ttf"] = os.path.join(GAME_ASSETS, "fonts", font + ".ttf")
    hashed["logo"] = os.path.join(GAME_ASSETS, "logos", "lmu_logo_icon.png")
    for code in {t["country"] for t in config.TRACKS.values()}:
        hashed["flag:" + code] = os.path.join(GAME_ASSETS, "flags", code + ".svg")

    missing = {src: dst for src, dst in wanted.items() if not os.path.exists(dst)}
    missing_hashed = {key: dst for key, dst in hashed.items() if not os.path.exists(dst)}
    if not missing and not missing_hashed:
        return
    if not (config.UI_ZIP and os.path.exists(config.UI_ZIP)):
        print("⚠️ Interface du jeu (Bin\\UI.zip) introuvable : logos, drapeaux et polices du jeu non disponibles.")
        return

    extracted = 0
    with zipfile.ZipFile(config.UI_ZIP) as z:
        names = set(z.namelist())
        for key, dst in missing_hashed.items():
            if key == "logo":
                src = _hashed(names, "lmu_logo_icon", ".png")
            else:
                # Deux drapeaux par pays (flag-icons) : 4:3 (640 x 480) et carré ; on garde le 4:3
                src = _hashed(names, key.split(":")[1], ".svg", lambda n: b'viewBox="0 0 640 480"' in z.read(n)[:400])
            if src:
                missing[src] = dst
        for src, dst in missing.items():
            if src not in names:   # variante absente du jeu (ex. pas de version « Dark ») : normal
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(z.read(src))
            extracted += 1
    if extracted:
        print(f"🎮 {extracted} fichier(s) extrait(s) du jeu dans assets/game/.")


def ensure_assets():
    extract_game_assets()
    trackmaps.fetch_missing()
