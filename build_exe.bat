@echo off
rem Fabrique dist\LMU-Chrono.exe : executable autonome, sans Python a installer chez l'utilisateur.
rem Prerequis : Python 3.10 ou plus recent. Un environnement isole .venv est cree dans le dossier du projet.
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe python -m venv .venv || exit /b 1
.venv\Scripts\python -m pip install --quiet --upgrade pip || exit /b 1
.venv\Scripts\python -m pip install --quiet -r requirements.txt pyinstaller || exit /b 1

rem --noconsole : pas de fenetre noire (icone pres de l'horloge) ; config.json, gabarit et icone integres
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --noconsole ^
    --name LMU-Chrono ^
    --icon lmu_dashboard\resources\icon.ico ^
    --add-data "config.json;." ^
    --add-data "lmu_dashboard\web_template.html;lmu_dashboard" ^
    --add-data "lmu_dashboard\resources;lmu_dashboard\resources" ^
    lmu.py || exit /b 1

echo.
echo Executable : %~dp0dist\LMU-Chrono.exe