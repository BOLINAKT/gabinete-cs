@echo off
setlocal
cd /d "%~dp0"

rem Abre o app do CS2 (app_cs.py). Mesmo padrao do RUN_PLAYS_WINDOWS.bat do LoL.
rem Python: o do app do LoL, que ja tem streamlit e pandas.
set "PYEXE=C:\Gabinetes\gabinetelolweb3.1\.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

rem Traz as odds que o robo coletou no GitHub. Nunca impede o app de abrir.
git pull --ff-only -q || echo [aviso] nao consegui puxar as odds novas - abrindo com as que ja tenho.

rem Porta 8520: pode ficar aberto junto com o app do LoL.
"%PYEXE%" -m streamlit run "app_cs.py" --server.port 8520 --browser.gatherUsageStats false

pause
