@echo off
cd /d "%~dp0"
echo Demarrage Children's Fruit...
venv\Scripts\python.exe manage.py runserver
pause
