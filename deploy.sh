#!/bin/bash

set -e

cd /var/www/debt_manager

echo "Обновляем код из GitHub..."
git pull origin master

echo "Активируем виртуальное окружение..."
source venv/bin/activate

echo "Устанавливаем зависимости..."
pip install -r requirements.txt

echo "Создаём таблицы в базе, если их нет..."
python - <<'PY'
from app import app, db

with app.app_context():
    db.create_all()

print("База данных проверена/создана")
PY

echo "Перезапускаем сервис..."
sudo systemctl reset-failed debt_manager
sudo systemctl restart debt_manager

echo "Статус сервиса:"
sudo systemctl status debt_manager --no-pager