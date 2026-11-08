"""Installation et désinstallation : raccourci « LMU Chrono » sur le bureau (créé une fois, au premier lancement),
suppression de l'exécutable, du raccourci et des données."""
import os
import sys

from . import config
from .i18n import t
from .winutil import desktop_dir, powershell, ps_quote

DONE_MARKER = os.path.join(config.DATA_DIR, ".raccourci_cree")   # pour ne pas le recréer s'il a été supprimé exprès


def shortcut_path():
    return os.path.join(desktop_dir(), config.APP_NAME + ".lnk")


def create_shortcut():
    """Crée le raccourci : l'exécutable (qui porte son icône), ou « pythonw lmu.py --tray » depuis le code source."""
    if config.FROZEN:
        target, arguments, icon = sys.executable, "", sys.executable
    else:
        # pythonw : la version de Python sans fenêtre de console
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        target = pythonw if os.path.exists(pythonw) else sys.executable
        arguments, icon = f'"{os.path.join(config.APP_DIR, "lmu.py")}" --tray', config.ICON_ICO
    # Création via l'objet COM WScript.Shell
    code, _, error = powershell(
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut({ps_quote(shortcut_path())});"
        f"$s.TargetPath = {ps_quote(target)}; $s.Arguments = {ps_quote(arguments)};"
        f"$s.WorkingDirectory = {ps_quote(config.DATA_DIR)}; $s.IconLocation = {ps_quote(icon)};"
        f"$s.Description = {ps_quote(t('shortcut_description'))}; $s.Save()"
    )
    if code != 0:
        print(f"⚠️ Raccourci sur le bureau non créé : {error}")
        return False
    with open(DONE_MARKER, "w", encoding="utf-8"):
        pass
    print(f"🖥️ Raccourci « {config.APP_NAME} » créé sur le bureau.")
    return True


def ensure_shortcut():
    if not os.path.exists(DONE_MARKER):
        create_shortcut()


def uninstall():
    """Programme la suppression du raccourci, de l'exécutable et du dossier des données, quelques secondes après
    l'arrêt du programme (un programme en cours ne peut pas supprimer son propre fichier ni sa base ouverte).
    Réservé à l'exécutable : depuis le code source, le dossier des données est celui du projet."""
    if not config.FROZEN or os.path.basename(config.DATA_DIR) != config.APP_NAME:
        raise RuntimeError(t("uninstall_exe_only"))
    commands = [
        "ping 127.0.0.1 -n 6 > nul",   # attente d'environ 5 secondes, le temps que LMU Chrono se ferme
        f'del /f /q "{shortcut_path()}"',
        f'del /f /q "{sys.executable}"',
        f'rmdir /s /q "{config.DATA_DIR}"',
    ]
    # L'exécutable PyInstaller place ses sous-processus dans un « job » Windows fermé avec lui : une commande lancée
    # directement serait tuée à l'arrêt du programme. Elle est donc créée par le service WMI, hors de ce job,
    # sans fenêtre (ShowWindow = 0).
    code, _, error = powershell(
        "$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow = [uint16]0};"
        "$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{"
        f"CommandLine = {ps_quote('cmd /c ' + ' & '.join(commands))}; ProcessStartupInformation = $si}};"
        "exit $r.ReturnValue"
    )
    if code != 0:
        raise RuntimeError(t("uninstall_failed", error=error or code))
