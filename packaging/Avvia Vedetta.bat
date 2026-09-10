@echo off
cd /d "%~dp0"
echo Negozi disponibili:
for %%f in (negozi\*.yaml) do echo    %%~nf
set /p NEGOZIO=Quale negozio? 
Vedetta\Vedetta.exe --config config.yaml --negozio %NEGOZIO%
pause
