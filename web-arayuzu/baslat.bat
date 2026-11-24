@echo off
cd /d "%~dp0"
echo HandPilot Car: http://localhost:4173
echo Durdurmak icin Control + C tuslarina basin.
py -m http.server 4173
pause
