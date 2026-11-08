"""Tracés des circuits, récupérés via l'API locale de LMU (jeu lancé, le menu principal suffit).

Pour chaque circuit, assets/game/trackmaps/ contient :
  - <scene>.svg      : le tracé dessiné comme dans le jeu, utilisé par la page
  - raw/<scene>.json : les points bruts, pour pouvoir redessiner sans le jeu
  - index.json       : sceneDesc -> nom, nom court, longueur, type (rempli par fetch_all)
"""
import json
import math
import os
import urllib.request

from . import config

GAME_API = "http://127.0.0.1:6397/rest/race/"   # API locale de LMU (port de l'interface du jeu)
TRACKMAPS_DIR = os.path.join(config.ASSETS_DIR, "game", "trackmaps")

# Rotation appliquée par le jeu à chaque tracé (getTrackMapRotation dans Bin\UI.zip), testée dans cet ordre
TRACK_MAP_ROTATION = [
    ("bahrain", 177.6), ("fuji", 307), ("lemans", 180), ("monza", 175), ("portimao", 196.3), ("sebring", 269.5),
    ("spa", 180), ("imola", 90), ("cota", -85), ("qatar", -151.3), ("paulricard", -104), ("barcelona", -32.9),
    ("daytona", 144), ("laguna", 156), ("longbeach", -92), ("roadatlanta", 155),
]


def track_map_svg(waypoints, scene):
    """Tracé du circuit en SVG, avec le même calcul que le composant TrackMap de l'interface du jeu :
    points de la trajectoire (type 0), rotation par circuit, cadre + marge de 5 %, trait blanc de 1 % de la taille,
    points trop éloignés (> 28 m) non reliés."""
    pts = [{"x": w["x"], "z": w["z"]} for w in waypoints if w.get("type") == 0]
    if not pts:
        return None
    zs, xs = [p["z"] for p in pts], [p["x"] for p in pts]
    width, height = math.ceil(abs(min(zs) - max(zs))), math.ceil(abs(min(xs) - max(xs)))
    padding = round(max(width, height) / 100) * 5
    cx = min(zs) + (width + padding) / 2
    cy = min(xs) + (height + padding) / 2
    angle = math.radians(next((a for key, a in TRACK_MAP_ROTATION if key in scene.lower()), 0))
    for p in pts:
        dz, dx = p["z"] - cx, p["x"] - cy
        p["z"], p["x"] = cx + math.cos(angle) * dz - math.sin(angle) * dx, cy + math.sin(angle) * dz + math.cos(angle) * dx
    zs, xs = [p["z"] for p in pts], [p["x"] for p in pts]
    vb_w = math.ceil(abs(min(zs) - max(zs))) + padding
    vb_h = math.ceil(abs(min(xs) - max(xs))) + padding
    vb_x, vb_y = math.ceil(min(zs) - padding / 2), math.ceil(min(xs) - padding / 2)
    stroke = round(max(vb_w, vb_h) / 100)

    def near(a, b):
        return math.hypot(a["z"] - b["z"], a["x"] - b["x"]) < 28

    d = [f"M{pts[0]['z']:.1f},{pts[0]['x']:.1f}"]
    for prev, p in zip(pts, pts[1:]):
        d.append(f"{'L' if near(p, prev) else 'M'}{p['z']:.1f},{p['x']:.1f}")
    if near(pts[0], pts[-1]):
        d.append(f"L{pts[0]['z']:.1f},{pts[0]['x']:.1f}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x} {vb_y} {vb_w} {vb_h}">'
            f'<path d="{" ".join(d)}" fill="none" stroke="#fff" stroke-width="{stroke}" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def _game_tracks():
    """Liste des circuits (toutes variantes) fournie par l'API locale du jeu, ou None si LMU n'est pas lancé."""
    try:
        with urllib.request.urlopen(GAME_API + "track", timeout=3) as resp:
            return json.load(resp)
    except Exception:
        return None


def _save_track_map(track):
    """Récupère les points d'un circuit via l'API et enregistre raw/<scene>.json et <scene>.svg."""
    scene = track["sceneDesc"]
    with urllib.request.urlopen(f"{GAME_API}track/{track['id']}/trackmap", timeout=20) as resp:
        raw = resp.read()
    os.makedirs(os.path.join(TRACKMAPS_DIR, "raw"), exist_ok=True)
    with open(os.path.join(TRACKMAPS_DIR, "raw", scene.lower() + ".json"), "wb") as f:
        f.write(raw)
    svg = track_map_svg(json.loads(raw), scene)
    if svg:
        with open(os.path.join(TRACKMAPS_DIR, scene.lower() + ".svg"), "w", encoding="utf-8") as f:
            f.write(svg)
    return bool(svg)


def fetch_missing():
    """Récupère les tracés manquants des circuits de la config (si LMU est lancé)."""
    scenes = {info["scene"] for info in config.TRACKS.values()}
    missing = [s for s in sorted(scenes) if not os.path.exists(os.path.join(TRACKMAPS_DIR, s.lower() + ".svg"))]
    if not missing:
        return
    tracks = _game_tracks()
    if tracks is None:
        print(f"ℹ️ LMU n'est pas lancé : {len(missing)} tracé(s) de circuit non récupéré(s), relancer avec le jeu ouvert.")
        return
    by_scene = {t.get("sceneDesc"): t for t in tracks}
    for scene in missing:
        if scene not in by_scene:
            print(f"⚠️ Circuit {scene} introuvable dans le jeu.")
        elif _save_track_map(by_scene[scene]):
            print(f"🗺️ Tracé {scene} récupéré depuis le jeu.")


def fetch_all():
    """Récupère les tracés de TOUS les circuits du jeu (LMU lancé), plus l'index index.json."""
    tracks = _game_tracks()
    if tracks is None:
        print("❌ LMU n'est pas lancé : ouvrez le jeu (le menu principal suffit) puis relancez.")
        return
    index, ok = {}, 0
    for track in sorted(tracks, key=lambda t: t.get("sceneDesc", "")):
        scene = track.get("sceneDesc")
        if not scene or "showroom" in scene.lower():
            continue
        index[scene] = {k: track.get(k) for k in ("name", "shortName", "length", "type", "id")}
        try:
            if _save_track_map(track):
                ok += 1
                print(f"🗺️ {scene:<28} {track.get('name')}")
            else:
                print(f"⚠️ {scene} : aucun point de trajectoire")
        except Exception as e:
            print(f"⚠️ {scene} : {e}")
    with open(os.path.join(TRACKMAPS_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"✅ {ok} tracé(s) enregistré(s) dans {TRACKMAPS_DIR}")
