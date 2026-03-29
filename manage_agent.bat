@echo off
setlocal
title Gmail Triage Agent Manager

echo ========================================
echo   GMAIL TRIAGE AGENT - CONTROL PANEL
echo ========================================
echo.
echo [1] EXAM MODE (Turn OFF all background tasks)
echo [2] NORMAL MODE (Turn ON all background tasks)
echo [3] STATUS Check
echo [Q] Quit
echo.

set /p choice="Choose an option: "

if "%choice%"=="1" goto EXAM_MODE
if "%choice%"=="2" goto NORMAL_MODE
if "%choice%"=="3" goto STATUS_CHECK
if "%choice%"=="q" goto end
if "%choice%"=="Q" goto end

:EXAM_MODE
echo.
echo Disabling background tasks...
schtasks /change /tn "GmailTriageAgent" /disable
schtasks /change /tn "GmailTriageBackup" /disable
echo Stopping any running agent processes...
taskkill /f /fi "WINDOWTITLE eq Gmail Triage Agent*" /t >nul 2>&1
echo.
echo [COMPLETE] Agent is now OFF. Good luck with your exam!
echo.
pause
goto end

:NORMAL_MODE
echo.
echo Enabling background tasks...
schtasks /change /tn "GmailTriageAgent" /enable
schtasks /change /tn "GmailTriageBackup" /enable
echo.
echo [COMPLETE] Agent is now ON and will run every 10 minutes.
echo.
pause
goto end

:STATUS_CHECK
echo.
echo --- Task Status ---
schtasks /query /tn "GmailTriageAgent" /fo list | findstr "Status"
schtasks /query /tn "GmailTriageBackup" /fo list | findstr "Status"
echo.
pause
goto end

:end
exit
