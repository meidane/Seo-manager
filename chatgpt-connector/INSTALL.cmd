@echo off
chcp 65001 >nul
title ChatGPT-WP - Install
cd /d "%~dp0"
if not exist "%~dp0plugin\app\install.mjs" (
  echo.
  echo  [!] First extract the ZIP: right-click the zip - Extract All - then run INSTALL.cmd from the extracted folder.
  echo  [!] اول فایل zip را Extract کن، بعد INSTALL.cmd را از پوشه باز شده اجرا کن.
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  [!] Node.js is not installed. Install the LTS version, then run INSTALL.cmd again.
  echo  [!] Node.js نصب نیست. نسخه LTS را نصب کن و دوباره INSTALL.cmd را اجرا کن.
  start "" https://nodejs.org/
  pause
  exit /b 1
)
node "%~dp0plugin\app\install.mjs"
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo  Opening panel...
node "%USERPROFILE%\.codex\plugins\seo-wp-connector\app\panel.mjs"
if errorlevel 1 pause
