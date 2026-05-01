import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', '')
    ADMIN_LOGIN_ENABLED = os.environ.get('ADMIN_LOGIN_ENABLED', 'false').lower() in ('1', 'true', 'yes', 'on')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
    TEST_USER_ENABLED = os.environ.get('TEST_USER_ENABLED', 'false').lower() in ('1', 'true', 'yes', 'on')
    TEST_USER_TELEGRAM_ID = int(os.environ.get('TEST_USER_TELEGRAM_ID', '-999999999999'))
    TEST_USER_USERNAME = os.environ.get('TEST_USER_USERNAME', 'testuser')
    TEST_USER_FIRST_NAME = os.environ.get('TEST_USER_FIRST_NAME', 'Тестовый')
    TEST_USER_LAST_NAME = os.environ.get('TEST_USER_LAST_NAME', 'Пользователь')
    TEST_USER_ROLE = os.environ.get('TEST_USER_ROLE', 'user')
    
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'debt_manager')
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        f"?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
