"""Dessine l'icône de LMU Chrono : chronomètre blanc sur des bandes diagonales aux couleurs de l'écran titre du jeu.

Produit lmu_dashboard/resources/icon.ico (exécutable, raccourci : 16 à 256 px) et icon.png (icône près de l'horloge,
onglet du navigateur). À relancer seulement si le dessin change :  python tools/make_icon.py   (nécessite Pillow)
"""
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lmu_dashboard", "resources")
S = 4            # dessin à 1024 px (coordonnées ci-dessous sur une grille de 256), réduit ensuite : bords lissés
WHITE = "#ffffff"


def p(*xy):
    return [v * S for v in xy]


def draw_icon():
    img = Image.new("RGBA", (256 * S, 256 * S), "#4a86c5")   # fond bleu clair
    d = ImageDraw.Draw(img)
    # Bandes diagonales : rouge, orange, bleu nuit
    d.polygon([tuple(p(-40, 256)), tuple(p(120, -20)), tuple(p(190, -20)), tuple(p(30, 256))], fill="#e8063c")
    d.polygon([tuple(p(30, 256)), tuple(p(190, -20)), tuple(p(230, -20)), tuple(p(70, 256))], fill="#f0502a")
    d.polygon([tuple(p(150, 256)), tuple(p(300, -20)), tuple(p(340, -20)), tuple(p(190, 256))], fill="#14182a")
    # Chronomètre : cadran, poussoir, aiguilles
    d.ellipse(p(128 - 72, 142 - 72, 128 + 72, 142 + 72), outline=WHITE, width=16 * S)
    d.rounded_rectangle(p(112, 40, 144, 62), radius=6 * S, fill=WHITE)
    for (x2, y2, w) in ((128, 96, 14), (160, 160, 10)):
        d.line(p(128, 142, x2, y2), fill=WHITE, width=w * S)
        d.ellipse(p(x2 - w / 2, y2 - w / 2, x2 + w / 2, y2 + w / 2), fill=WHITE)   # bout arrondi
    d.ellipse(p(128 - 9, 142 - 9, 128 + 9, 142 + 9), fill=WHITE)
    # Coins arrondis
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=56 * S, fill=255)
    img.putalpha(mask)
    return img


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    big = draw_icon().resize((256, 256), Image.LANCZOS)
    big.save(os.path.join(OUT_DIR, "icon.png"))
    big.save(os.path.join(OUT_DIR, "icon.ico"), sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])
    print("Icône écrite dans", OUT_DIR)
