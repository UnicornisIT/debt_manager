#!/bin/bash

set -e

cd /var/www/debt_manager

echo "Обновляем код из GitHub..."
git pull origin master

echo "Активируем виртуальное окружение..."
source venv/bin/activate

echo "Устанавливаем зависимости..."
pip install -r requirements.txt

echo "Применяем миграции базы данных..."
export FLASK_APP=app.py
python - <<'PY'
from app import app
from extensions import db
from sqlalchemy import inspect
from flask_migrate import stamp

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if 'alembic_version' not in tables and tables:
        print('Существующая схема найдена, добавляем метку текущей миграции...')
        stamp()
PY
flask db upgrade

echo "Перезапускаем сервис..."
sudo systemctl reset-failed debt_manager
sudo systemctl restart debt_manager

echo "Статус сервиса:"
sudo systemctl status debt_manager --no-pager