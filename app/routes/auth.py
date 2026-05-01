from datetime import datetime
from flask import jsonify, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from app import login_manager
from app.models import User
from app.services.telegram_auth_service import verify_telegram_login
from app.utils import get_dictionary_values, get_setting, record_activity


class AdminUser(UserMixin):
    def __init__(self):
        self.id = 'admin'
        self.username = 'admin'
        self.first_name = 'Администратор'
        self.role = 'superadmin'
        self.is_blocked = False

    @property
    def is_admin(self):
        return True

    @property
    def is_superadmin(self):
        return True

    def get_id(self):
        return str(self.id)


class LocalTestUser(UserMixin):
    def __init__(self):
        self.id = 'test-user'
        self.username = 'testuser'
        self.first_name = 'Тестовый'
        self.last_name = 'Пользователь'
        self.role = 'user'
        self.is_blocked = False
        self.login_count = 1
        self.last_login_ip = None
        self.last_user_agent = None
        self.is_local_test_user = True

    @property
    def is_admin(self):
        return False

    @property
    def is_superadmin(self):
        return False

    def get_id(self):
        return str(self.id)


def init_app(app):
    @login_manager.user_loader
    def load_user(user_id):
        if not user_id:
            return None
        if str(user_id) == 'admin':
            return AdminUser()
        if str(user_id) == 'test-user':
            return LocalTestUser()
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        return redirect(url_for('login'))

    @app.before_request
    def require_login():
        allowed_endpoints = {'static', 'login', 'telegram_login', 'logout', 'admin_login', 'test_login'}
        if request.endpoint in allowed_endpoints:
            return

        if getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'is_admin', False):
            if not request.path.startswith('/admin'):
                return redirect(url_for('admin_dashboard'))

        if getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'is_blocked', False):
            logout_user()
            if request.path.startswith('/api/'):
                return {'success': False, 'error': 'Учетная запись заблокирована'}, 403
            return render_template('login.html', error='Ваша учётная запись заблокирована.', bot_username=app.config.get('TELEGRAM_BOT_USERNAME', ''), telegram_allowed=False)

        if not getattr(current_user, 'is_authenticated', False):
            return unauthorized()

    @app.context_processor
    def inject_user():
        app_name = get_setting('app_name', 'ДолгТрекер')
        bank_options = get_dictionary_values('bank')
        admin_login_enabled = app.config.get('ADMIN_LOGIN_ENABLED', False)
        test_login_enabled = app.config.get('TEST_USER_ENABLED', False)
        return dict(
            current_user=current_user,
            app_name=app_name,
            bank_options=bank_options,
            admin_login_enabled=admin_login_enabled,
            test_login_enabled=test_login_enabled,
        )

    @app.route('/login')
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        telegram_allowed = get_setting('telegram_login_enabled', app.config.get('TELEGRAM_LOGIN_ENABLED', 'true'))
        if isinstance(telegram_allowed, str):
            telegram_allowed = telegram_allowed.lower() in ('1', 'true', 'yes', 'on')
        return render_template(
            'login.html',
            bot_username=app.config.get('TELEGRAM_BOT_USERNAME', ''),
            telegram_allowed=telegram_allowed,
            admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False),
            test_login_enabled=app.config.get('TEST_USER_ENABLED', False),
        )

    @app.route('/test-login')
    def test_login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        test_user_enabled = app.config.get('TEST_USER_ENABLED', False)
        if not test_user_enabled:
            return render_template(
                'login.html',
                error='Тестовый доступ отключён.',
                bot_username=app.config.get('TELEGRAM_BOT_USERNAME', ''),
                telegram_allowed=False,
                admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False),
                test_login_enabled=False,
            )

        test_user_telegram_id = app.config.get('TEST_USER_TELEGRAM_ID', -999999999999)
        test_user = None
        try:
            test_user = User.query.filter_by(telegram_id=test_user_telegram_id).first()
            if not test_user:
                test_user = User(
                    telegram_id=test_user_telegram_id,
                    username=app.config.get('TEST_USER_USERNAME', 'testuser'),
                    first_name=app.config.get('TEST_USER_FIRST_NAME', 'Тестовый'),
                    last_name=app.config.get('TEST_USER_LAST_NAME', 'Пользователь'),
                    auth_date=datetime.utcnow(),
                    role=app.config.get('TEST_USER_ROLE', 'user'),
                )
                db.session.add(test_user)

            if getattr(test_user, 'is_blocked', False):
                return render_template(
                    'login.html',
                    error='Тестовый пользователь заблокирован.',
                    bot_username=app.config.get('TELEGRAM_BOT_USERNAME', ''),
                    telegram_allowed=False,
                    admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False),
                    test_login_enabled=True,
                )

            test_user.login_count = (test_user.login_count or 0) + 1
            test_user.last_login_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            test_user.last_user_agent = request.headers.get('User-Agent')
            db.session.commit()
            login_user(test_user)
            return redirect(url_for('index'))
        except SQLAlchemyError:
            login_user(LocalTestUser())
            return redirect(url_for('index', login_mode='local-test'))

    @app.route('/telegram-login')
    def telegram_login():
        data = request.args.to_dict()
        bot_username = app.config.get('TELEGRAM_BOT_USERNAME', '')

        telegram_allowed = get_setting('telegram_login_enabled', app.config.get('TELEGRAM_LOGIN_ENABLED', 'true'))
        if isinstance(telegram_allowed, str):
            telegram_allowed = telegram_allowed.lower() in ('1', 'true', 'yes', 'on')
        if not telegram_allowed:
            return render_template('login.html', error='Вход через Telegram временно отключён администратором.', bot_username=bot_username, telegram_allowed=False, admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False))

        if not verify_telegram_login(data, app.config.get('TELEGRAM_BOT_TOKEN', '')):
            return render_template('login.html', error='Ошибка авторизации через Telegram. Проверьте настройки бота.', bot_username=bot_username, telegram_allowed=telegram_allowed, admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False))

        telegram_id = data.get('id')
        if not telegram_id:
            return render_template('login.html', error='Неверные данные авторизации.', bot_username=bot_username, telegram_allowed=telegram_allowed, admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False))

        user = User.query.filter_by(telegram_id=int(telegram_id)).first()
        auth_date = datetime.utcfromtimestamp(int(data.get('auth_date', '0')))
        if not user:
            user = User(
                telegram_id=int(telegram_id),
                username=data.get('username'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                photo_url=data.get('photo_url'),
                auth_date=auth_date,
            )
            if not User.query.filter(User.role.in_(['admin', 'superadmin'])).first():
                user.role = 'superadmin'
            db.session.add(user)
        else:
            if user.is_blocked:
                return render_template('login.html', error='Ваш аккаунт заблокирован. Обратитесь к администратору.', bot_username=bot_username, telegram_allowed=False, admin_login_enabled=app.config.get('ADMIN_LOGIN_ENABLED', False))
            user.username = data.get('username')
            user.first_name = data.get('first_name')
            user.last_name = data.get('last_name')
            user.photo_url = data.get('photo_url')
            user.auth_date = auth_date

        user.login_count = (user.login_count or 0) + 1
        user.last_login_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user.last_user_agent = request.headers.get('User-Agent')

        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin_dashboard'))

        admin_login_enabled = app.config.get('ADMIN_LOGIN_ENABLED', False)
        admin_password = app.config.get('ADMIN_PASSWORD', '')
        error_message = None

        if request.method == 'POST':
            if not admin_login_enabled or not admin_password:
                error_message = 'Админ-вход отключён или пароль не настроен.'
            else:
                password = request.form.get('password', '')
                if password == admin_password:
                    login_user(AdminUser())
                    return redirect(url_for('admin_dashboard'))
                error_message = 'Неверный пароль администратора.'

        return render_template('admin_login.html', admin_login_enabled=admin_login_enabled, error_message=error_message)

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('login'))
