# CLAUDE.md — LMU Chrono

Contexte pour reprendre le développement de **LMU Chrono**, un outil personnel devenu un projet partagé sur GitHub.
Ce fichier résume l'état du projet, les décisions prises avec l'utilisateur et les pièges déjà rencontrés.

## Le projet en une phrase

LMU Chrono affiche dans le navigateur, avec le style de l'interface du jeu, les **meilleurs temps au tour du joueur
sur Le Mans Ultimate** (LMU), par classe et par circuit. Il les compare aux temps de référence de la communauté.
Il est distribué en **exécutable Windows autonome** (`LMU-Chrono.exe`), sans configuration, pour tout joueur de LMU.

## Travailler avec l'utilisateur

- **Langue** : toujours répondre en **français**. Le code, les commentaires et les messages affichés sont en français.
- **Explications** : quand il les demande, détailler chaque modification (quoi, où, pourquoi), avec des liens vers
  les fichiers.
- **Fidélité au jeu** : le rendu doit rester proche de l'interface de LMU (badges de classe, polices, couleurs,
  tracés). Les éléments graphiques viennent des fichiers du jeu chaque fois que c'est possible.
- **Essais visuels** : pour un choix de design, proposer **plusieurs variantes en test**, avec des boutons de
  bascule dans un panneau « Test » fixé en bas à droite de la page (`body[data-<clé>]` + CSS par variante, choix
  mémorisé dans `localStorage`). Une fois la variante retenue, supprimer les autres variantes et le panneau.
- **Images** : **demander avant de dessiner soi-même** un logo, un badge ou une icône. Une demande explicite de
  propositions d'icônes vaut accord.
- **Vocabulaire** : ne jamais afficher le mot « alien » dans l'interface. On dit « temps de référence » ou
  « Temps réf. ». Le mot reste permis dans le code (`alien_times`, `alien_sheet_csv_url`).
- **Confidentialité** : ne pas faire apparaître le nom de pilote de l'utilisateur dans ce qui est publié (README,
  captures `docs/`). L'aperçu du README est anonymisé (« PILOTE LMU »).
- **Vérification** : après chaque modification visible, régénérer la page et contrôler une capture (voir
  « Tester »). Annoncer clairement ce qui a été vérifié et ce qui ne l'a pas été.
- **Exécutable** : **ne jamais fabriquer l'exe (`build_exe.bat`) sans demande explicite de l'utilisateur**. Les
  modifications se testent en mode code source (`python lmu.py`, `--serve`, `--tray`).
- **Bilingue (français / anglais)** : **tout ce que voit l'utilisateur existe dans les deux langues**, à chaque
  évolution : la page, le menu de l'icône, les notifications, les fenêtres Windows, les messages d'actualisation
  et **les deux README** (`README.md` en anglais, `README.fr.md` en français, à mettre à jour ensemble, captures
  `docs/preview.png` et `docs/apercu.png` comprises). Ne jamais ajouter un texte visible dans une seule langue.
  Seuls le code, ses commentaires, les journaux et ce fichier restent en français. Voir « Langues ».

## Lancer le projet

```bat
pip install -r requirements.txt          :: pystray, Pillow (inutiles pour un simple python lmu.py)
python lmu.py                            :: lit les nouveaux XML, génère Meilleurs_Temps_LMU.html
python lmu.py --serve --open             :: serveur local avec console (bouton ↻ et réglages actifs)
python lmu.py --tray                     :: comme l'exécutable : icône près de l'horloge, sans console
python lmu.py --aliens                   :: re-télécharge les temps de référence
python lmu.py --rebuild                  :: relit tous les XML depuis zéro
python lmu.py --all-tracks               :: (LMU lancé) récupère les tracés de tous les circuits
build_exe.bat                            :: fabrique dist\LMU-Chrono.exe (dans un .venv isolé)
```

Depuis le code source, les données restent **dans le dossier du projet** (`lmu.db`, `assets/`, la page générée).
Avec l'exécutable, elles vont dans **`%LOCALAPPDATA%\LMU Chrono`**.

## Architecture

```
lmu.py                     point d'entrée (options ci-dessus ; exe sans option = --tray)
config.json                classes, correspondance des circuits, tracés, marques (configuration partagée)
lmu_dashboard/
  config.py                chemins, config.json, settings.json (réglages perso), dossier du jeu
  steam.py                 recherche de LMU dans les bibliothèques Steam (registre + libraryfolders.vdf)
  data.py                  XML de résultats → SQLite ; détection du joueur ; temps de référence (Google Sheets)
  assets.py                extraction depuis Bin\UI.zip : logos de marques, drapeaux, polices, logo « LM »
  trackmaps.py             tracés des circuits via l'API locale du jeu (http://127.0.0.1:6397/rest/race/)
  web.py                   données + images (data URI) → page HTML autonome à partir de web_template.html
  web_template.html        toute la page : CSS, HTML, JavaScript
  pipeline.py              refresh() : base → images → page, protégé par un verrou
  server.py                serveur 127.0.0.1:8765 : page, ↻, réglages, choix de dossier, désinstallation
  tray.py                  icône près de l'horloge (pystray) : ouvrir, actualiser, dossier des données, quitter
  install.py               raccourci sur le bureau, désinstallation
  i18n.py                  langue (réglage ou langue de Windows) et textes côté Python, en français et en anglais
  winutil.py               fenêtres de message, Bureau, PowerShell, fenêtre de choix de dossier
  resources/icon.ico|png   icône de LMU Chrono (dessin original, généré par tools/make_icon.py)
tools/make_icon.py         dessine l'icône (Pillow)
build_exe.bat              PyInstaller --onefile --noconsole
.github/workflows/release.yml   à la publication d'une release GitHub : fabrique l'exe et le joint à la release
README.md / README.fr.md   README anglais (celui que GitHub affiche) et français, avec un lien vers l'autre langue
docs/preview.png, apercu.png   captures des README (anonymisées : « LMU DRIVER » / « PILOTE LMU »)
old/                       archives personnelles (anciens scripts, échantillons XML) : ignoré par Git, ne pas modifier
```

**Flux** : `refresh()` → `data.sync_results` (nouveaux XML seulement, table `processed_files`) →
`data.update_alien_times` si demandé → `data.get_best_table` → `assets.ensure_assets` (fichiers du jeu manquants,
tracés manquants si le jeu tourne) → `web.export_web` (page autonome, tout en data URI).

**Base SQLite** (`lmu.db`) : `processed_files`, `laps` (meilleur tour du joueur par fichier et session
Qualification/Course), `alien_times`, `new_records` (badges « Nouveau record »). Les colonnes `fastest_car` et `fastest_time` d'`alien_times` sont inutilisées.

## Sources de données

- **Résultats** : `<jeu>\UserData\Log\Results\*.xml`, au format rFactor. Le circuit est dans `TrackCourse`, les
  sessions dans `Qualify` et `Race`, les pilotes dans `Driver` (`Name`, `CarClass`, `CarType`, `BestLapTime`,
  `isPlayer`). `load_xml` répare les fichiers corrompus (octets nuls, contenu après `</rFactorXML>`).
- **Temps de référence** : Google Sheets public « LMU laptimes » d'**Ohne Speed**, export CSV (`pub?output=csv`).
  La colonne « ~100% » donne le temps de référence, la colonne Q (index 16) la classe. Ils sont téléchargés à chaque
  lancement de l'exe ; en cas d'échec, l'ancienne table est gardée.
- **Interface du jeu** : `<jeu>\Bin\UI.zip` (zip de 1,2 Go), lu sans être extrait en entier.
  - `start/images/manufacturer/Brand=X.svg` : logo pour fond sombre ; `Brand=X Dark.svg` : pour fond clair.
  - `start/assets/<code pays>-<empreinte 8 car.>.svg` : drapeaux flag-icons. Deux par pays ; on garde le 4:3,
    `viewBox="0 0 640 480"`.
  - `start/assets/lmu_logo_icon-<empreinte>.png` : monogramme « LM » du bandeau.
  - `start/fonts/` : Antonio-SemiBold (titres) et Heebo 400/600/700 (texte).
  - Les **noms à empreinte changent avec les versions du jeu** : ils se cherchent par motif, jamais par nom fixe.
- **Tracés** : API locale du jeu, active seulement **quand LMU tourne**. `GET track` donne la liste (`sceneDesc`),
  `GET track/{id}/trackmap` les points ; les points de type 0 forment la trajectoire. Ils sont dessinés comme dans
  le jeu par `track_map_svg` : rotation par circuit, marge de 5 %, trait de 1 %, pas de liaison entre deux points à
  plus de 28 m.
- **Les fichiers `.mas` du jeu sont chiffrés : ne pas chercher à les décoder.**

## config.json

- `classes` : `xml` (CarClass des XML), `name` (titre affiché), `alien` (classe dans le sheet), `color`, `tab`
  (nom court), `badge` (texte du badge), `badge_corner` (triangle orange de LMP2 ELMS).
- `circuit_corresp_alien` : nom du circuit dans les XML → nom court du sheet (affiché et clé de `tracks`).
- `tracks` : nom court → `country` (code ISO du drapeau) et `scene` (identifiant du tracé dans le jeu).
- `brands` : marques reconnues en début de `CarType` (logo `Brand=<marque>.svg`). `class_tokens` : mots retirés
  du nom de voiture affiché.
- **Tous les circuits du jeu sont couverts** (vérifié contre l'API du jeu et le sheet en novembre 2026). Règle des
  noms dans les XML : une variante porte son nom propre (API `name`, ex. « Bahrain Outer Circuit »), le tracé
  principal le nom du circuit (API `shortName` sans la version, ex. « Circuit of the Americas »). Barcelone et
  Paul Ricard principal ne sont pas confirmés : deux orthographes sont enregistrées pour chacun. Les variantes ELMS
  (IMOLAELMS…) sont les mêmes tracés que les WEC.
- **Ajouter un circuit** (mise à jour du jeu) : une entrée dans `circuit_corresp_alien` et une dans `tracks`. Une
  ligne « Circuits sans correspondance » dans la sortie signale un oubli. `python lmu.py --all-tracks`, jeu lancé,
  régénère `assets/game/trackmaps/index.json`, la liste officielle des circuits.
- **Nom de voiture affiché** : `CarType` sans la marque ni les désignations de classe (`class_tokens`, suffixe
  collé compris : « LMGT3.R »). « GT3 » et « GTE » ne sont pas retirés, car ils font partie de noms de modèles
  (« 911 GT3 R »). Si rien ne reste (« Mercedes-AMG LMGT3 »), on affiche la marque.

## Choix de design validés (ne pas revenir dessus sans demande)

- **Bandeau** compact aux 4 coins arrondis, dégradé et rayures de l'écran titre du jeu. À gauche : monogramme
  « LM » en blanc, titre « MEILLEURS TEMPS », pastille blanche avec le nom de la classe active, nom du pilote en
  dessous. À droite : un encart blanc (`rgba(255,255,255,.92)`) contenant les badges de classe, un séparateur, ↻ et
  la roue crantée.
- **Badges de classe** reproduits du jeu, dans l'ordre HY · P2E · P2 · P3 · GTE · GT3 (inverse de la config).
  Carré de 32 px en Antonio. Au repos : fond blanc, cadre et texte à la couleur de la classe. Au survol ou
  sélectionné : fond de la couleur de la classe. Le triangle ELMS est découpé au bord du badge
  (`overflow: clip; overflow-clip-margin: border-box`), sinon il dépasse d'un pixel en position fractionnaire.
- **Encarts** : posés sur le fond de la page, sans panneau. Grille `1fr 2fr 1fr 2fr` : Circuits | Meilleur écart |
  Écart moyen | Dernière session. Ils ont la largeur du tableau hors colonne NB. La valeur et le circuit sont
  séparés par une barre et centrés chacun dans sa moitié ; le circuit est en majuscules.
  - Meilleur écart et Dernière session sont cliquables : défilement jusqu'à la ligne, qui clignote.
  - Écart moyen est cliquable : tri du tableau par écart.
- **Tableau** :
  - largeurs de colonnes identiques pour toutes les classes (`measureColumns`) ;
  - blocs Circuit | Qualification | Course | Référence séparés par des colonnes vides à pointillés espacés ;
  - titres de groupes soulignés à la couleur de la classe ;
  - lignes transparentes, en verre au survol.
- **Contenu des colonnes** :
  - **Circuit** : tracé blanc, trait vertical, drapeau à la hauteur des majuscules, nom court en majuscules (le
    nom officiel est en info-bulle) ;
  - **NB** : sessions roulées, largeur de 4 chiffres ;
  - **Voiture** : logo du jeu et modèle sans la classe ;
  - **Date** : date sur une ligne, heure en petit dessous ;
  - **Écart** : pourcentage, jauge graduée et palier (Élite < 1 %, Compétitif < 2 %, Bon < 4 %, Milieu < 6 %,
    Fond grille < 7 %, Hors rythme) ;
  - une ★ marque le meilleur tour de la ligne.
- **Polices** : Antonio pour les titres (toujours `font-weight: normal`, sans italique, car elle n'existe qu'en
  SemiBold dans le jeu), Heebo pour le texte.
- **Thèmes clair et sombre** : un script en tête de page pose `html[data-theme]` avant l'affichage. Sa valeur est
  le choix mémorisé (`localStorage` `lmu-theme`, réglé dans la roue crantée : Automatique / Clair / Sombre) ou, à
  défaut, le thème du système. Les couleurs sombres dépendent de `[data-theme="dark"]`, jamais de
  `@media (prefers-color-scheme)`. En thème clair, les tracés blancs sont inversés en gris foncé.
- **Badge « NEW »** (nouveau record ; Heebo gras droit, blanc sur une forme rouge aux coins arrondis (3 px), coupée
  en biais à droite et dessinée par deux pseudo-éléments, car un clip-path ne sait pas arrondir ; 12 px
  de haut, texte centré : 2 px de rouge au-dessus et en dessous ; à la place de l'étoile à côté du temps ; ancien
  temps et gain en info-bulle) : temps
  améliorés lors de la dernière actualisation qui a apporté des sessions (table `new_records`). Ces records
  remplacent ceux de l'actualisation précédente. Une première session sur un circuit n'est pas un record, et une
  relecture complète (`rebuild`) efface les badges.

## Langues (français / anglais)

- **Choix** : réglage `language` de `settings.json` (`fr` ou `en`), posé par les **drapeaux de la roue crantée**
  (drapeaux du jeu : France et Royaume-Uni, boutons « Français » / « English »). Sans réglage : langue de Windows
  (français si l'interface de Windows est en français, sinon anglais). Le changement est **immédiat** dans la
  page ; `POST /api/language` l'enregistre, régénère la page et fait suivre le menu de l'icône et les messages.
- **Textes de la page** : objet `I18N` (`fr` et `en`) au début du script de `web_template.html`, lu par
  `t(clé, {paramètres})`. Les textes fixes du HTML portent `data-i18n="clé"` (ou `data-i18n-aria`) ; le pied de
  page, le tableau, les encarts et les infobulles sont refaits par `refreshLanguage()`, qui remesure aussi les
  colonnes (les libellés n'ont pas la même longueur). Python ne met pas de texte dans la page : ses messages
  d'aide sont des clés (`{"key": "notice_missing_maps", "n": 3}`) traduites par la page.
- **Textes de Python** : `lmu_dashboard/i18n.py` (`STRINGS["fr"]` et `["en"]`, `t(clé, **paramètres)`) : menu de
  l'icône (textes en fonctions, donc à jour sans redémarrer), notifications, fenêtres Windows, messages
  d'actualisation, erreurs de réglages, page d'attente, description du raccourci.
- **Ajouter un texte** : toujours dans les deux langues, avec la même clé. Vérifier ensuite qu'aucun texte français
  ne reste en dur dans la page (hors noms propres : Le Mans Ultimate, noms de circuits, de classes, « Français »).
- **Formats** : pourcentage « +1.85 % » en français, « +1.85% » en anglais ; décimale de l'infobulle du badge NEW
  (0,62 / 0.62) ; noms de pays de l'infobulle des drapeaux par `Intl.DisplayNames`. Les dates restent `jj/mm/aa` et
  les temps `mm:ss:cc` dans les deux langues. Les circuits, classes et marques gardent leur nom (celui du jeu).
- **Mêmes proportions dans les deux langues** : `measureColumns` mesure les colonnes dans chaque langue
  (`measureWidths`) et garde la plus grande largeur de chacune ; le français, aux libellés les plus longs, donne les
  proportions et l'anglais les reprend. Tableau et encarts ont la même taille quelle que soit la langue (vérifié :
  mêmes largeurs de colonnes, 1 451 px, encarts 1 408 px). Un libellé plus long qu'un autre élargit la colonne dans
  les deux langues, sans être coupé.
- **Vocabulaire anglais** : Qualifying / Race / Reference ; Track (circuit), No. (nombre de sessions), Time, Car, Gap,
  Ref. time ; paliers Elite / Competitive / Good / Midpack / Tail-ender / Off pace (ceux du sheet d'Ohne Speed).

## Distribution (exe, GitHub)

- **Aucune configuration** :
  - le jeu est trouvé via Steam ;
  - le joueur est **le nom marqué `isPlayer=1` présent dans le plus de fichiers**, les sessions hors ligne
    départageant. `isPlayer` seul ne suffit pas : en ligne, tous les pilotes humains l'ont ;
  - les réglages manuels (nom, dossier du jeu) passent par la roue crantée et vont dans `settings.json`. Tout
    changement relit toute la base (`refresh(rebuild=True)`). La langue et le thème s'appliquent tout de suite, sans
    relecture.
- **Exe** : PyInstaller `--onefile --noconsole`, environ 15 Mo.
  - Le double-clic lance le mode icône : mise à jour, temps de référence, raccourci au premier lancement, ouverture
    de la page.
  - Sans console, les messages vont dans `lmu-chrono.log` et les erreurs s'affichent dans une fenêtre Windows.
  - Un second lancement rouvre seulement la page.
- **Désinstallation** (roue crantée, exe uniquement) : supprime le raccourci, l'exe et le dossier des données.
- **Droits** : ne jamais versionner ni distribuer de fichier du jeu (`assets/` est ignoré). Ils sont lus chez le
  joueur. L'icône de LMU Chrono est un dessin original et peut être publiée.
- **Crédits obligatoires** dans le README et le pied de page :
  - **Ohne Speed**, avec le lien vers son sheet. Il n'a pas encore été prévenu ; retirer le lien s'il le demande.
  - flag-icons (licence MIT), embarqué par le jeu.
  - La mention « projet de fan non officiel ».
- **Publier une version** : sur GitHub, Releases > Draft a new release > étiquette `vX.Y.Z` > Publish. Le workflow
  fabrique l'exe et le joint. Licence MIT ; la ligne de copyright est à mettre au nom ou au pseudo GitHub choisi par
  l'utilisateur.

## Pièges déjà rencontrés

- **Windows et port** : `HTTPServer` active `SO_REUSEADDR` ; sous Windows, une 2ᵉ instance peut alors ouvrir le même
  port. `ExclusiveHTTPServer` utilise `SO_EXCLUSIVEADDRUSE`.
- **PyInstaller onefile** : les sous-processus sont tués à la fermeture de l'exe (job object). Une commande qui doit
  lui survivre, comme le nettoyage de la désinstallation, est créée via **WMI** (`Win32_Process.Create`).
- **Sans console** (`--noconsole`, pythonw) : `sys.stdout` vaut `None`, d'où la redirection vers le journal. Avec
  une sortie redirigée, les emojis des messages plantent l'encodage cp1252 (`reconfigure(errors="replace")`).
- **`.bat`** : écrire en **ASCII avec fins de ligne CRLF**. Un `.bat` en UTF-8 ou LF est mal lu par cmd.
- **PowerShell 5.1** (shell de l'environnement) : pas de `&&` ; préférer des scripts Python dans un dossier
  temporaire aux `python -c` contenant des guillemets ; `Get-Content`/`Set-Content` sans `-Encoding` abîment
  l'UTF-8 ; un `foreach` ne se pipe pas.
- **CSS** : le raccourci `font:` remet `line-height` à `normal`. Toujours écrire `font: normal 15px/1.45 …`, sinon
  la mise en page se décale de quelques pixels.
- **Centrage vertical des lignes du tableau** : il se mesure sur l'**encre** (pixels dessinés), entre les traits de
  séparation, et non sur les boîtes. Heebo dessine chiffres et majuscules 1 à 2 px au-dessus du centre de sa
  ligne : les cellules de texte ont `padding: 6px 12px 4px`. La colonne Circuit reste à 5 / 5, et Antonio y est
  remonté par `padding-bottom: 0.25em`. Écart obtenu : moins de 0,6 px partout.
- **Badges** en position fractionnaire : le cadre est calé au pixel, pas le pseudo-élément (voir le clip ci-dessus).
- **Logos de marques** : dans les fichiers du jeu, le dessin n'est pas centré dans son cadre (carré de 64 px, marges
  variables). Au chargement, `measureLogo` (canvas) mesure la partie **visible** de chaque logo sur le fond de son
  thème, car des parties sombres sont invisibles sur fond sombre. `alignLogos` le décale ensuite pour qu'il soit
  centré sur l'encre du nom du modèle, 1 px au-dessus du centre de la cellule (`LOGO_TEXT_OFFSET`). Un logo blanc
  sans version « fond clair » (ADESS) est affiché en noir en thème clair. Pour vérifier, une planche de gros plans
  juge mieux qu'une mesure sur capture, qui rate les traits fins.
- **Le Google Sheets** ne s'analyse pas en HTML (« No tables found ») : utiliser l'export CSV.

## Tester

- **Capture de la page** : `python tools/capture.py <sortie.png> [--theme light|dark] [--lang fr|en] [--class CLÉ]
  [--player NOM] [--width] [--height]` (Edge sans interface, dans une copie temporaire de la page : thème, langue,
  classe affichée et nom du pilote forcés). Les captures du README se font avec `--player "LMU DRIVER"` /
  `"PILOTE LMU"`. Une modification de texte ou de mise en page se vérifie **dans les deux langues**.
- **Commandes** : lancer des commandes **Python seules** (`python lmu.py`, `python tools/capture.py …`,
  `python <script de test>`), sans tube (`|`), variable PowerShell ni `Start-Process`. Elles sont autorisées sans
  demande. Une vérification complexe s'écrit dans un script Python temporaire. Ne pas demander à l'utilisateur de
  lancer `lmu.py` lui-même : le faire, ou ouvrir la page pour lui (`os.startfile`).
- **Une variante ou un état précis** : copier la page générée dans un dossier temporaire, en remplaçant l'appel
  d'initialisation, par exemple en forçant `localStorage` `lmu-class`.
- **Mesures au pixel** : scripts PIL sur les captures, par exemple pour le centrage vertical ou un dépassement.
- **Non-régression** : comparer les données injectées (`const DATA = …`) de l'ancienne et de la nouvelle page, puis
  faire une différence de pixels entre captures.
- **Serveur** : le tester sur un **autre port** (sous-classe de `DashboardHandler` dans un script de test) pour ne
  pas gêner l'instance de l'utilisateur.
- **Exe** : tester sur une **copie** dans un dossier temporaire, car la désinstallation supprime l'exe testé.
  Vérifier `%LOCALAPPDATA%\LMU Chrono` avant et après, et ne jamais arrêter une instance lancée par l'utilisateur.
- **Avant de refabriquer l'exe** : vérifier qu'aucun `LMU-Chrono.exe` ne tourne, sinon le fichier est verrouillé.
  Demander à l'utilisateur de quitter le sien par l'icône.
- **Permissions** : `.claude/settings.local.json` autorise sans demande `python *`, `.venv\Scripts\python *`,
  `.\build_exe.bat*` et les lectures PowerShell (`Get-ChildItem`, `Get-Content`, `Get-Item`, `Get-Process`,
  `Test-Path`, `Select-String`). Privilégier ces commandes, simples et non enchaînées.

## Pistes non réalisées

- Lancement automatique au démarrage de Windows (proposé, non demandé).
- Signature de l'exe, pour éviter l'avertissement SmartScreen (certificat payant).
- Test chez un autre joueur : en cours. Points à surveiller : la détection du nom, un jeu hors bibliothèque Steam
  standard, les faux positifs d'antivirus.
