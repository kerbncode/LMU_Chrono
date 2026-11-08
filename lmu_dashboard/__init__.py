"""LMU Chrono : base des meilleurs tours du joueur de Le Mans Ultimate et page web façon interface du jeu.

Modules :
  config     configuration (config.json, settings.json) et chemins
  steam      recherche du jeu dans les bibliothèques Steam
  data       lecture des XML de résultats (et détection du joueur), temps de référence (Google Sheets), base SQLite
  assets     images et polices de la page, tirées de Bin\\UI.zip du jeu
  trackmaps  tracés des circuits (API locale du jeu)
  web        export de la page web (web_template.html)
  pipeline   mise à jour complète : base + page
  server     serveur local de la page (actualisation, réglages, désinstallation)
  tray       icône près de l'horloge (exécutable lancé par double-clic)
  install    raccourci sur le bureau, désinstallation
  i18n       langue de l'interface (français / anglais) : textes produits côté Python
  winutil    fonctions Windows : messages, choix de dossier, PowerShell
"""
