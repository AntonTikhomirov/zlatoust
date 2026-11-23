@echo off
rem Запуск с консолью — удобно, если что-то пошло не так и нужно видеть сообщения.
cd /d "%~dp0\.."
".venv\Scripts\python.exe" -m zlatoust
