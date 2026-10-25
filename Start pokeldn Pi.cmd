@echo off
rem Starts pokeldn on its Pi page with the Raspberry Pi radio chosen (bin\pi_launch.py).
rem POKELDN_PYTHON and POKELDN_DATA override the Python and data folder; by default a
rem gui-venv and gui-data next to this checkout are used when present.
setlocal
cd /d "%~dp0"
if not defined POKELDN_PYTHON if exist "%~dp0..\gui-venv\Scripts\pythonw.exe" set "POKELDN_PYTHON=%~dp0..\gui-venv\Scripts\pythonw.exe"
if not defined POKELDN_PYTHON if exist "%~dp0.venv\Scripts\pythonw.exe" set "POKELDN_PYTHON=%~dp0.venv\Scripts\pythonw.exe"
if not defined POKELDN_PYTHON set "POKELDN_PYTHON=pythonw"
if not defined POKELDN_DATA if exist "%~dp0..\gui-data\settings.json" set "POKELDN_DATA=%~dp0..\gui-data"
start "pokeldn Pi" "%POKELDN_PYTHON%" "%~dp0bin\pi_launch.py"
