@echo off
cd /d "%~dp0"
echo Negozi disponibili:
for %%f in (negozi\*.yaml) do echo    %%~nf
set /p NEGOZIO=Quale negozio? 
set /p NOME=Nome del riquadro (come scritto in negozi\%NEGOZIO%.yaml): 
Vedetta\Vedetta.exe zone --config config.yaml --negozio %NEGOZIO% --source %NOME%
pause
