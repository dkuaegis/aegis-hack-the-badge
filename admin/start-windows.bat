@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0start.py" %*
) else (
  python "%~dp0start.py" %*
)
exit /b %errorlevel%
