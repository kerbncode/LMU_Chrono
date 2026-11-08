"""Recherche du dossier d'installation de Le Mans Ultimate dans les bibliothèques Steam."""
import os
import re
import winreg

LMU_APP_ID = "2399420"


def _steam_dir():
    for root, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                      (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
        try:
            with winreg.OpenKey(root, key) as k:
                value = winreg.QueryValueEx(k, "SteamPath" if root == winreg.HKEY_CURRENT_USER else "InstallPath")[0]
                return os.path.normpath(value)
        except OSError:
            continue
    return None


def _libraries(steam_dir):
    """Bibliothèques Steam (dossier principal + autres disques), lues dans steamapps\\libraryfolders.vdf."""
    libraries = [steam_dir]
    try:
        with open(os.path.join(steam_dir, "steamapps", "libraryfolders.vdf"), encoding="utf-8") as f:
            text = f.read()
        libraries += [os.path.normpath(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', text)]
    except OSError:
        pass
    return list(dict.fromkeys(libraries))


def find_game_dir():
    """Dossier du jeu (…\\steamapps\\common\\Le Mans Ultimate), ou None s'il n'est pas trouvé."""
    steam_dir = _steam_dir()
    if not steam_dir:
        return None
    for library in _libraries(steam_dir):
        manifest = os.path.join(library, "steamapps", f"appmanifest_{LMU_APP_ID}.acf")
        if not os.path.exists(manifest):
            continue
        with open(manifest, encoding="utf-8") as f:
            match = re.search(r'"installdir"\s+"([^"]+)"', f.read())
        game_dir = os.path.join(library, "steamapps", "common", match.group(1) if match else "Le Mans Ultimate")
        if os.path.isdir(game_dir):
            return game_dir
    return None
