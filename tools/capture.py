"""Outil de développement : capture d'écran de la page générée avec Edge sans interface.

  python tools/capture.py sortie.png [--theme light|dark] [--lang fr|en] [--class CLÉ] [--player NOM]
                                     [--width 1600] [--height 1000] [--page fichier.html]

Dans une copie temporaire de la page : le thème est forcé via le choix mémorisé (localStorage « lmu-theme »), la
langue via DATA.language, la classe affichée via « lmu-class » (clé XML : GT3, LMP2_ELMS…), et --player remplace
le nom du pilote (captures du README).
"""
import argparse
import os
import re
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                    r"Microsoft\Edge\Application\msedge.exe")


def capture(output, theme=None, lang=None, cls=None, player=None, width=1600, height=1000, page=None):
    page = page or os.path.join(ROOT, "Meilleurs_Temps_LMU.html")
    with open(page, encoding="utf-8") as f:
        html = f.read()
    if lang:
        html = re.sub(r'"language": "\w+"', f'"language": "{lang}"', html, count=1)
    if player is not None:
        html = re.sub(r'"player": "[^"]*"', lambda m: f'"player": "{player}"', html, count=1)
    storage = "".join(f'localStorage.setItem("{k}", "{v}");' for k, v in (("lmu-theme", theme), ("lmu-class", cls)) if v)
    if storage:
        html = html.replace('<link rel="icon" id="favicon">', f'<link rel="icon" id="favicon"><script>{storage}</script>', 1)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html)
    try:
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width},{height}",
                        "--virtual-time-budget=4000", f"--screenshot={os.path.abspath(output)}",
                        "file:///" + tmp.name.replace(os.sep, "/")], check=True, capture_output=True)
    finally:
        os.remove(tmp.name)
    print("capture :", os.path.abspath(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--theme", choices=["light", "dark"])
    parser.add_argument("--lang", choices=["fr", "en"])
    parser.add_argument("--class", dest="cls")
    parser.add_argument("--player")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--page")
    a = parser.parse_args()
    capture(a.output, a.theme, a.lang, a.cls, a.player, a.width, a.height, a.page)
