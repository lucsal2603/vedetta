@echo off
cd /d "%~dp0"
echo Negozi disponibili (o scrivi un nome nuovo):
for %%f in (negozi\*.yaml) do echo    %%~nf
set /p NEGOZIO=Quale negozio? 
echo Fra 5 secondi viene fotografato lo schermo: porta davanti il client con la vista giusta.
timeout /t 5 >nul
Vedetta\Vedetta.exe riquadri --config config.yaml --negozio %NEGOZIO% --write
pause
