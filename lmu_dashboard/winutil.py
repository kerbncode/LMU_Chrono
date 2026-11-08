"""Fonctions propres à Windows : fenêtres de message, dossier du bureau, choix d'un dossier, commandes PowerShell."""
import ctypes
import subprocess

from . import config


def message_box(text, error=False):
    """Fenêtre de message Windows (l'exécutable n'a pas de console)."""
    MB_ICONERROR, MB_ICONINFORMATION, MB_TOPMOST = 0x10, 0x40, 0x40000
    ctypes.windll.user32.MessageBoxW(None, text, config.APP_NAME,
                                     (MB_ICONERROR if error else MB_ICONINFORMATION) | MB_TOPMOST)


def desktop_dir():
    """Bureau de l'utilisateur (même redirigé vers OneDrive)."""
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf)   # 0x10 = CSIDL_DESKTOPDIRECTORY
    return buf.value


def ps_quote(value):
    """Chaîne PowerShell entre apostrophes (une apostrophe s'y double)."""
    return "'" + value.replace("'", "''") + "'"


def powershell(script):
    """Exécute un script PowerShell sans fenêtre ; retourne (code de sortie, sortie en UTF-8, erreurs)."""
    script = "[Console]::OutputEncoding = [Text.Encoding]::UTF8;" + script
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-STA", "-Command", script],
                            capture_output=True, encoding="utf-8", errors="replace",
                            creationflags=subprocess.CREATE_NO_WINDOW)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def browse_folder(description, initial=None):
    """Fenêtre Windows de choix d'un dossier, au premier plan ; retourne le dossier choisi ou None."""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
        f"$d.Description = {ps_quote(description)}; $d.ShowNewFolderButton = $false;"
        + (f"$d.SelectedPath = {ps_quote(initial)};" if initial else "")
        + "$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true};"
        "if ($d.ShowDialog($owner) -eq 'OK') { $d.SelectedPath }"
    )
    code, out, _ = powershell(script)
    return out if code == 0 and out else None
