"""Données LMU : lecture des XML de résultats, temps de référence et base SQLite.

La base (lmu.db) contient :
  - processed_files : XML déjà analysés (seuls les nouveaux sont lus à chaque lancement)
  - laps            : meilleur tour du joueur pour chaque session Qualification / Course
  - alien_times     : temps de référence du Google Sheets (mis à jour à la demande)
"""
import collections
import csv
import functools
import glob
import io
import os
import re
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

from . import config

# Balise XML de la section -> libellé de session
SESSION_TAGS = {"Qualify": "Qualification", "Race": "Course"}
DATE_DB_FORMAT = "%Y-%m-%d %H:%M:%S"

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_files (
    filename     TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL,
    status       TEXT NOT NULL          -- ok | error
);
CREATE TABLE IF NOT EXISTS laps (
    filename  TEXT NOT NULL,
    session   TEXT NOT NULL,            -- Qualification | Course
    circuit   TEXT NOT NULL,
    car_class TEXT NOT NULL,
    car_type  TEXT NOT NULL,
    best_lap  REAL NOT NULL,            -- secondes
    date      TEXT,                     -- YYYY-MM-DD HH:MM:SS
    PRIMARY KEY (filename, session)
);
CREATE INDEX IF NOT EXISTS idx_laps_class_circuit ON laps (car_class, circuit, session);
CREATE TABLE IF NOT EXISTS alien_times (
    alien_class  TEXT NOT NULL,
    track        TEXT NOT NULL,
    alien_time   REAL NOT NULL,         -- secondes, colonne "~100%"
    fastest_car  TEXT,
    fastest_time REAL,
    PRIMARY KEY (alien_class, track)
);
CREATE TABLE IF NOT EXISTS new_records (    -- temps améliorés lors de la dernière actualisation apportant des sessions
    car_class     TEXT NOT NULL,
    circuit       TEXT NOT NULL,
    session       TEXT NOT NULL,            -- Qualification | Course
    previous_best REAL NOT NULL,            -- ancien record, secondes
    best_lap      REAL NOT NULL,            -- nouveau record, secondes
    PRIMARY KEY (car_class, circuit, session)
);
"""


def connect():
    conn = sqlite3.connect(config.DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# --- Formats ---

def format_lap_time(seconds):
    """Secondes -> MM:SS:cc (minutes:secondes:centièmes)."""
    if not seconds or seconds <= 0:
        return ""
    total_cs = round(seconds * 100)
    minutes, rem = divmod(total_cs, 6000)
    secs, cs = divmod(rem, 100)
    return f"{minutes:02d}:{secs:02d}:{cs:02d}"


def parse_sheet_time(text):
    """'1:58.50' (format du Google Sheets) -> secondes. None si invalide ou nul."""
    m = re.fullmatch(r"\s*(\d+):(\d{1,2}(?:\.\d+)?)\s*", text or "")
    if not m:
        return None
    seconds = int(m.group(1)) * 60 + float(m.group(2))
    return seconds if seconds > 0 else None


# --- Lecture des XML ---

def load_xml(path):
    """Parse un XML LMU ; tente une réparation si le fichier est corrompu (octets nuls, contenu en trop)."""
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8", errors="replace")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        end = text.find("</rFactorXML>")
        if end != -1:
            text = text[: end + len("</rFactorXML>")]
        return ET.fromstring(text)


def parse_xml_file(path, player_name):
    """Meilleur tour du joueur pour chaque session Qualification / Course du fichier."""
    race_results = load_xml(path).find("RaceResults")
    if race_results is None:
        return []

    circuit = (race_results.findtext("TrackCourse") or race_results.findtext("TrackVenue") or "Inconnu").strip()
    laps = []
    for section in race_results:
        session = SESSION_TAGS.get(section.tag)
        if session is None:
            continue
        time_string = section.findtext("TimeString") or race_results.findtext("TimeString")
        try:
            date = datetime.strptime(time_string.strip(), "%Y/%m/%d %H:%M:%S").strftime(DATE_DB_FORMAT)
        except (AttributeError, ValueError):
            date = None

        for driver in section.findall("Driver"):
            if (driver.findtext("Name") or "").strip() != player_name:
                continue
            try:
                best_lap = float(driver.findtext("BestLapTime") or 0)
            except ValueError:
                best_lap = 0
            if best_lap <= 0:
                continue
            laps.append({
                "filename": os.path.basename(path),
                "session": session,
                "circuit": circuit,
                "car_class": (driver.findtext("CarClass") or "Inconnu").strip(),
                "car_type": (driver.findtext("CarType") or "Inconnu").strip(),
                "best_lap": best_lap,
                "date": date,
            })
    return laps


def result_files():
    return glob.glob(os.path.join(config.RESULTS_DIR, "*.xml")) if config.RESULTS_DIR else []


def player_name():
    """Nom du joueur : réglage "player_name", sinon déduit des XML."""
    return config.SETTINGS.get("player_name") or detect_player_name()


@functools.cache
def detect_player_name():
    """Nom du joueur déduit des XML (mis en cache ; detect_player_name.cache_clear() si le dossier du jeu change).

    Le jeu marque <isPlayer>1</isPlayer> le joueur… mais aussi tous les pilotes humains d'une course en ligne :
    le joueur est celui qui apparaît dans le plus de fichiers (il est dans tous les siens).
    À égalité (peu de fichiers), les sessions hors ligne, où il est le seul humain, départagent.
    """
    files_seen, offline = collections.Counter(), collections.Counter()
    for path in sorted(result_files(), key=os.path.getmtime, reverse=True)[:40]:
        try:
            race_results = load_xml(path).find("RaceResults")
        except (ET.ParseError, OSError):
            continue
        names_in_file = set()
        for section in race_results if race_results is not None else []:
            humans = [(d.findtext("Name") or "").strip() for d in section.findall("Driver")
                      if (d.findtext("isPlayer") or "").strip() == "1"]
            names_in_file.update(humans)
            if len(humans) == 1:
                offline[humans[0]] += 1
        files_seen.update(n for n in names_in_file if n)
    if not files_seen:
        return None
    return max(files_seen, key=lambda n: (files_seen[n], offline[n]))


def _best_laps(conn):
    """Meilleur tour par (classe, circuit, session)."""
    return {(r[0], r[1], r[2]): r[3] for r in conn.execute(
        "SELECT car_class, circuit, session, MIN(best_lap) FROM laps GROUP BY car_class, circuit, session")}


def _update_new_records(conn, previous):
    """Nouveaux records : temps meilleurs qu'avant cette actualisation (pas les premières sessions sur un circuit).
    Ils remplacent ceux de l'actualisation précédente ; sans nouvelle session, l'appelant garde les anciens."""
    records = [(*key, previous[key], best) for key, best in _best_laps(conn).items()
               if key in previous and best < previous[key] - 1e-6]
    conn.execute("DELETE FROM new_records")
    conn.executemany("INSERT INTO new_records VALUES (?, ?, ?, ?, ?)", records)
    if records:
        print(f"🏆 {len(records)} nouveau(x) record(s).")


def sync_results(conn, rebuild=False):
    """Analyse les XML pas encore présents en base. rebuild=True vide la table et relit tout."""
    if rebuild:
        conn.execute("DELETE FROM laps")
        conn.execute("DELETE FROM processed_files")
        conn.execute("DELETE FROM new_records")   # tout serait « nouveau » : pas de badge après une relecture
    previous = _best_laps(conn)

    done = {row[0] for row in conn.execute("SELECT filename FROM processed_files")}
    new_files = [p for p in result_files() if os.path.basename(p) not in done]
    print(f"🔍 {len(new_files)} nouveau(x) fichier(s) XML à analyser ({len(done)} déjà en base).")
    player = player_name()
    if not player:
        print("ℹ️ Aucun résultat de course trouvé : jouez une session dans LMU puis relancez.")
        return 0, 0

    now = datetime.now().strftime(DATE_DB_FORMAT)
    added = 0
    for path in sorted(new_files):
        filename = os.path.basename(path)
        try:
            laps = parse_xml_file(path, player)
        except (ET.ParseError, OSError) as e:
            # Fichier peut-être en cours d'écriture par le jeu : on retentera au prochain lancement
            print(f"❌ Fichier illisible, ignoré pour cette fois : {filename} ({e})")
            continue
        conn.executemany(
            "INSERT OR REPLACE INTO laps VALUES (:filename, :session, :circuit, :car_class, :car_type, :best_lap, :date)",
            laps,
        )
        conn.execute("INSERT OR REPLACE INTO processed_files VALUES (?, ?, 'ok')", (filename, now))
        added += len(laps)
    if added and not rebuild:
        _update_new_records(conn, previous)
    conn.commit()
    print(f"💾 {added} session(s) ajoutée(s) pour {player}.")
    return len(new_files), added


# --- Temps de référence (Google Sheets) ---

def update_alien_times(conn):
    """Télécharge l'export CSV du Google Sheets publié et remplace la table alien_times.

    Le sheet empile un bloc par classe ; chaque ligne de données a la piste en
    colonne B et la classe en colonne Q. Retourne le nombre de temps chargés (0 si échec).
    """
    try:
        with urllib.request.urlopen(config.ALIEN_CSV_URL, timeout=20) as resp:
            text = resp.read().decode("utf-8")
    except Exception as e:
        print(f"⚠️ Google Sheets inaccessible ({e}) : les temps de référence en base sont conservés.")
        return 0

    rows = list(csv.reader(io.StringIO(text)))
    header = next((r for r in rows if len(r) > 1 and r[1] == "Track" and "~100%" in r), None)
    alien_col = header.index("~100%") if header else 4
    car_col = header.index("Fastest car") if header and "Fastest car" in header else 12
    best_col = header.index("Laptime") if header and "Laptime" in header else 13

    records = []
    for row in rows:
        if len(row) <= 16 or not row[1] or not row[16]:
            continue
        alien = parse_sheet_time(row[alien_col])
        if alien:
            records.append((row[16], row[1], alien, row[car_col] or None, parse_sheet_time(row[best_col])))

    if not records:
        print("⚠️ Aucun temps de référence trouvé dans le Google Sheets : format modifié ? Base inchangée.")
        return 0
    conn.execute("DELETE FROM alien_times")
    conn.executemany("INSERT INTO alien_times VALUES (?, ?, ?, ?, ?)", records)
    conn.commit()
    print(f"📊 {len(records)} temps de référence mis à jour.")
    return len(records)


def alien_times_count(conn):
    return conn.execute("SELECT COUNT(*) FROM alien_times").fetchone()[0]


# --- Données pour l'affichage ---

def get_best_table(conn):
    """Tableau des meilleurs temps, par classe (ordre de config.json) puis par circuit.

    Retourne [{"class": cfg, "rows": [{circuit, sessions, qualif, course, alien, best, gap}]}], toutes les classes
    de la config, même sans session ; qualif / course valent None ou {best_lap, date (datetime), car_type,
    record_previous (ancien record si ce temps est un nouveau record, sinon None)}.
    """
    records = {(r["car_class"], r["circuit"], r["session"]): r for r in conn.execute("SELECT * FROM new_records")}
    best = {}
    for row in conn.execute("SELECT * FROM laps ORDER BY best_lap DESC"):
        # Tri décroissant : le dernier écrit pour une clé est le plus rapide
        record = records.get((row["car_class"], row["circuit"], row["session"]))
        best.setdefault((row["car_class"], row["circuit"]), {})[row["session"]] = {
            "best_lap": row["best_lap"],
            "date": datetime.strptime(row["date"], DATE_DB_FORMAT) if row["date"] else None,
            "car_type": row["car_type"],
            "record_previous": record["previous_best"] if record and abs(record["best_lap"] - row["best_lap"]) < 1e-6 else None,
        }
    aliens = {(r["alien_class"], r["track"]): r["alien_time"] for r in conn.execute("SELECT * FROM alien_times")}
    # Nombre de sessions roulées (qualifications + courses) par classe et circuit
    session_counts = {(r[0], r[1]): r[2] for r in conn.execute(
        "SELECT car_class, circuit, COUNT(*) FROM laps GROUP BY car_class, circuit")}

    known_classes = {c["xml"] for c in config.CLASSES}
    unknown_classes = {k[0] for k in best} - known_classes
    if unknown_classes:
        print(f"⚠️ Classes absentes de config.json (ignorées) : {', '.join(sorted(unknown_classes))}")
    missing_circuits = {k[1] for k in best if k[1] not in config.CIRCUIT_CORRESP}
    if missing_circuits:
        print(f"⚠️ Circuits sans correspondance dans config.json : {', '.join(sorted(missing_circuits))}")

    table = []
    for class_cfg in config.CLASSES:
        rows = []
        for (car_class, circuit), sessions in sorted(best.items(), key=lambda kv: kv[0][1]):
            if car_class != class_cfg["xml"]:
                continue
            q, c = sessions.get("Qualification"), sessions.get("Course")
            alien = aliens.get((class_cfg["alien"], config.CIRCUIT_CORRESP.get(circuit)))
            best_lap = min(s["best_lap"] for s in (q, c) if s)
            rows.append({
                "circuit": circuit,
                "sessions": session_counts.get((car_class, circuit), 0),
                "qualif": q,
                "course": c,
                "alien": alien,
                "best": best_lap,
                "gap": (best_lap - alien) / alien if alien else None,
            })
        table.append({"class": class_cfg, "rows": rows})
    return table
