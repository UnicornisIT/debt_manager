@echo off
chcp 65001 > nul

cd /d "%~dp0"

echo ================================
echo Запуск debt_manager
echo ================================

if not exist venv (
    echo Создаю виртуальное окружение...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Обновляю pip...
python -m pip install --upgrade pip

echo Устанавливаю зависимости...
python -m pip install -r requirements.txt

if not exist .env (
    echo Файл .env не найден.
    echo Создаю .env из .env.example...
    copy .env.example .env
    echo.
    echo ВАЖНО: открой файл .env и укажи настройки базы данных.
    pause
)

echo Запускаю приложение...
python run.py

pause