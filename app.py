from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, current_user, login_user, logout_user
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from extensions import db
from config import Config
import hashlib
import hmac
import time


login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    return app


app = create_app()


@login_manager.user_loader
def load_user(user_id):
    from models import User
    if not user_id:
        return None
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
    return redirect(url_for('login'))


@app.before_request
def require_login():
    allowed_endpoints = {'static', 'login', 'telegram_login', 'logout'}
    if request.endpoint in allowed_endpoints:
        return
    if not getattr(current_user, 'is_authenticated', False):
        return unauthorized()


@app.context_processor
def inject_user():
    return dict(current_user=current_user)


# ──────────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────────


def parse_decimal(value, field_name, required=True):
    """Безопасно парсит десятичное число из строки"""
    if value is None or str(value).strip() == '':
        if required:
            raise ValueError(f"Поле '{field_name}' обязательно для заполнения")
        return None
    try:
        result = Decimal(str(value).replace(',', '.'))
        if result < 0:
            raise ValueError(f"Поле '{field_name}' не может быть отрицательным")
        return result
    except InvalidOperation:
        raise ValueError(f"Поле '{field_name}' содержит некорректное число")


def parse_date(value, field_name, required=False):
    """Безопасно парсит дату из строки"""
    if not value or str(value).strip() == '':
        if required:
            raise ValueError(f"Поле '{field_name}' обязательно для заполнения")
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Поле '{field_name}' содержит некорректную дату (формат: ГГГГ-ММ-ДД)")


def verify_telegram_login(data):
    bot_token = app.config.get('TELEGRAM_BOT_TOKEN', '')
    if not bot_token:
        return False

    auth_date = data.get('auth_date')
    hash_value = data.get('hash')
    if not auth_date or not hash_value:
        return False

    try:
        auth_timestamp = int(auth_date)
    except ValueError:
        return False

    if auth_timestamp > time.time() + 300:
        return False
    if time.time() - auth_timestamp > 86400:
        return False

    check_data = []
    for key, value in data.items():
        if key == 'hash':
            continue
        check_data.append(f'{key}={value}')
    check_data.sort()
    data_check_string = '\n'.join(check_data)

    secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hash, hash_value)


# ──────────────────────────────────────────────────────────────
# Аутентификация
# ──────────────────────────────────────────────────────────────


@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html', bot_username=app.config.get('TELEGRAM_BOT_USERNAME', ''))


@app.route('/telegram-login')
def telegram_login():
    data = request.args.to_dict()
    bot_username = app.config.get('TELEGRAM_BOT_USERNAME', '')

    if not verify_telegram_login(data):
        return render_template('login.html', error='Ошибка авторизации через Telegram. Проверьте настройки бота.', bot_username=bot_username)

    from models import User
    telegram_id = data.get('id')
    if not telegram_id:
        return render_template('login.html', error='Неверные данные авторизации.', bot_username=bot_username)

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
        db.session.add(user)
    else:
        user.username = data.get('username')
        user.first_name = data.get('first_name')
        user.last_name = data.get('last_name')
        user.photo_url = data.get('photo_url')
        user.auth_date = auth_date

    db.session.commit()
    login_user(user)
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# ──────────────────────────────────────────────────────────────
# Основные страницы
# ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Главный дашборд"""
    from models import Debt
    active_debts = Debt.query.filter_by(status='active', user_id=current_user.id).order_by(db.case((Debt.next_payment_date.is_(None), 1), else_=0), Debt.next_payment_date.asc()).all()
    
    # Сводная статистика
    total_remaining = sum(float(d.remaining_amount) for d in active_debts)
    total_original = sum(float(d.total_amount) for d in active_debts)
    
    # Ближайший платеж
    today = date.today()
    upcoming = [d for d in active_debts if d.next_payment_date and d.next_payment_date >= today]
    nearest_debt = upcoming[0] if upcoming else None
    
    # Просроченные
    overdue_count = len([d for d in active_debts if d.next_payment_date and d.next_payment_date < today])
    
    return render_template('index.html',
        debts=active_debts,
        total_remaining=total_remaining,
        total_original=total_original,
        active_count=len(active_debts),
        nearest_debt=nearest_debt,
        overdue_count=overdue_count,
        today=today,
    )


def get_user_debt(debt_id):
    from models import Debt
    return Debt.query.filter_by(id=debt_id, user_id=current_user.id).first()


@app.route('/archive')
def archive():
    """Страница архива"""
    from models import Debt
    archived_debts = Debt.query.filter_by(status='archived', user_id=current_user.id).order_by(Debt.updated_at.desc()).all()
    return render_template('archive.html', debts=archived_debts)


# ──────────────────────────────────────────────────────────────
# API для долгов
# ──────────────────────────────────────────────────────────────

@app.route('/api/debts', methods=['GET'])
def api_get_debts():
    """Получить список долгов с фильтрацией"""
    from models import Debt
    status = request.args.get('status', 'active')
    bank_filter = request.args.get('bank', '').strip()
    type_filter = request.args.get('type', '').strip()

    query = Debt.query.filter_by(status=status, user_id=current_user.id)
    if bank_filter:
        query = query.filter(Debt.bank_name.ilike(f'%{bank_filter}%'))
    if type_filter:
        query = query.filter_by(debt_type=type_filter)

    debts = query.order_by(db.case((Debt.next_payment_date.is_(None), 1), else_=0), Debt.next_payment_date.asc()).all()
    return jsonify({'success': True, 'debts': [d.to_dict() for d in debts]})


@app.route('/api/debts', methods=['POST'])
def api_create_debt():
    """Создать новый долг"""
    from models import Debt
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    try:
        # Валидация обязательных полей
        bank_name = str(data.get('bank_name', '')).strip()
        if not bank_name:
            raise ValueError("Название банка обязательно")

        debt_type = str(data.get('debt_type', '')).strip()
        if debt_type not in ('credit_card', 'split'):
            raise ValueError("Тип долга: выберите 'credit_card' или 'split'")

        product_name = str(data.get('product_name', '')).strip()
        if not product_name:
            raise ValueError("Название продукта/карты обязательно")

        total_amount = parse_decimal(data.get('total_amount'), 'Сумма долга', required=True)
        remaining_amount = parse_decimal(data.get('remaining_amount'), 'Остаток долга', required=True)
        minimum_payment = parse_decimal(data.get('minimum_payment'), 'Минимальный платеж', required=False)
        interest_rate = parse_decimal(data.get('interest_rate'), 'Процентная ставка', required=False)
        next_payment_date = parse_date(data.get('next_payment_date'), 'Дата следующего платежа')

        if remaining_amount > total_amount:
            raise ValueError("Остаток долга не может превышать общую сумму")

        debt = Debt(
            user_id=current_user.id,
            bank_name=bank_name,
            debt_type=debt_type,
            product_name=product_name,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            minimum_payment=minimum_payment,
            interest_rate=interest_rate,
            next_payment_date=next_payment_date,
            comment=str(data.get('comment', '')).strip() or None,
            status='active',
        )
        db.session.add(debt)
        db.session.commit()
        return jsonify({'success': True, 'debt': debt.to_dict()}), 201

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Ошибка сервера: {str(e)}'}), 500


@app.route('/api/debts/<int:debt_id>', methods=['GET'])
def api_get_debt(debt_id):
    """Получить один долг"""
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404
    return jsonify({'success': True, 'debt': debt.to_dict()})


@app.route('/api/debts/<int:debt_id>', methods=['PUT'])
def api_update_debt(debt_id):
    """Обновить долг"""
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    try:
        if 'bank_name' in data:
            bank_name = str(data['bank_name']).strip()
            if not bank_name:
                raise ValueError("Название банка обязательно")
            debt.bank_name = bank_name

        if 'debt_type' in data:
            if data['debt_type'] not in ('credit_card', 'split'):
                raise ValueError("Некорректный тип долга")
            debt.debt_type = data['debt_type']

        if 'product_name' in data:
            product_name = str(data['product_name']).strip()
            if not product_name:
                raise ValueError("Название продукта обязательно")
            debt.product_name = product_name

        if 'total_amount' in data:
            debt.total_amount = parse_decimal(data['total_amount'], 'Сумма долга', required=True)
        if 'remaining_amount' in data:
            debt.remaining_amount = parse_decimal(data['remaining_amount'], 'Остаток долга', required=True)
        if 'minimum_payment' in data:
            debt.minimum_payment = parse_decimal(data['minimum_payment'], 'Минимальный платеж', required=False)
        if 'interest_rate' in data:
            debt.interest_rate = parse_decimal(data['interest_rate'], 'Процентная ставка', required=False)
        if 'next_payment_date' in data:
            debt.next_payment_date = parse_date(data['next_payment_date'], 'Дата следующего платежа')
        if 'comment' in data:
            debt.comment = str(data['comment']).strip() or None

        if float(debt.remaining_amount) > float(debt.total_amount):
            raise ValueError("Остаток долга не может превышать общую сумму")

        debt.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'debt': debt.to_dict()})

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Ошибка сервера: {str(e)}'}), 500


@app.route('/api/debts/<int:debt_id>/archive', methods=['POST'])
def api_archive_debt(debt_id):
    """Архивировать долг"""
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404

    debt.status = 'archived'
    debt.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Карточка перемещена в архив'})


@app.route('/api/debts/<int:debt_id>/restore', methods=['POST'])
def api_restore_debt(debt_id):
    """Восстановить долг из архива"""
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404

    debt.status = 'active'
    debt.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Карточка восстановлена', 'debt': debt.to_dict()})


@app.route('/api/debts/<int:debt_id>/delete', methods=['DELETE'])
def api_delete_debt(debt_id):
    """Удалить долг полностью"""
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404

    db.session.delete(debt)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Карточка удалена'})


# ──────────────────────────────────────────────────────────────
# API для платежей
# ──────────────────────────────────────────────────────────────

@app.route('/api/debts/<int:debt_id>/payments', methods=['GET'])
def api_get_payments(debt_id):
    """История платежей по долгу"""
    from models import Payment
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404

    payments = Payment.query.filter_by(debt_id=debt_id).order_by(Payment.payment_date.desc()).all()
    return jsonify({
        'success': True,
        'debt': debt.to_dict(),
        'payments': [p.to_dict() for p in payments]
    })


@app.route('/api/debts/<int:debt_id>/payments', methods=['POST'])
def api_add_payment(debt_id):
    """Внести платеж"""
    from models import Payment
    debt = get_user_debt(debt_id)
    if not debt:
        return jsonify({'success': False, 'error': 'Долг не найден'}), 404
    if debt.status != 'active':
        return jsonify({'success': False, 'error': 'Нельзя вносить платеж в архивный долг'}), 422

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    try:
        amount = parse_decimal(data.get('amount'), 'Сумма платежа', required=True)
        if amount <= 0:
            raise ValueError("Сумма платежа должна быть больше нуля")

        payment_date_str = data.get('payment_date')
        if payment_date_str:
            payment_date = parse_date(payment_date_str, 'Дата платежа')
        else:
            payment_date = date.today()

        # Вычисляем новый остаток
        new_remaining = max(Decimal('0'), debt.remaining_amount - amount)
        
        # Сохраняем платеж
        payment = Payment(
            debt_id=debt_id,
            amount=amount,
            payment_date=payment_date,
            comment=str(data.get('comment', '')).strip() or None,
            remaining_after_payment=new_remaining,
        )
        debt.remaining_amount = new_remaining
        debt.updated_at = datetime.utcnow()

        db.session.add(payment)
        db.session.commit()

        # Проверяем, погашен ли долг
        debt_cleared = float(new_remaining) <= 0.01

        return jsonify({
            'success': True,
            'payment': payment.to_dict(),
            'debt': debt.to_dict(),
            'debt_cleared': debt_cleared,
        })

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 422
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Ошибка сервера: {str(e)}'}), 500


# ──────────────────────────────────────────────────────────────
# Инициализация базы данных и тестовые данные
# ──────────────────────────────────────────────────────────────

@app.route('/api/init-db', methods=['POST'])
def init_db_route():
    """Инициализация БД и загрузка тестовых данных"""
    from models import Debt, Payment
    db.create_all()
    
    # Добавляем тестовые данные только если БД пустая
    if Debt.query.filter_by(user_id=current_user.id).count() == 0:
        seed_data()
    
    return jsonify({'success': True, 'message': 'База данных инициализирована'})


def seed_data():
    """Добавление тестовых данных"""
    from models import Debt, Payment
    today = date.today()

    def shift_month(base_date, offset):
        month = base_date.month + offset
        year = base_date.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        return year, month

    def next_payment_day(day, threshold_day):
        if today.day < threshold_day:
            return date(today.year, today.month, day)
        year, month = shift_month(today, 1)
        return date(year, month, day)

    def previous_month_day(day, offset):
        year, month = shift_month(today, offset)
        return date(year, month, day)

    debts = [
        Debt(
            user_id=current_user.id,
            bank_name='Тинькофф',
            debt_type='credit_card',
            product_name='Тинькофф Платинум',
            total_amount=Decimal('85000'),
            remaining_amount=Decimal('47500'),
            minimum_payment=Decimal('3200'),
            interest_rate=Decimal('28.9'),
            next_payment_date=next_payment_day(25, 25),
            comment='Основная кредитная карта',
            status='active',
        ),
        Debt(
            user_id=current_user.id,
            bank_name='Сбербанк',
            debt_type='split',
            product_name='СберСплит — MacBook Pro',
            total_amount=Decimal('180000'),
            remaining_amount=Decimal('120000'),
            minimum_payment=Decimal('15000'),
            interest_rate=None,
            next_payment_date=next_payment_day(15, 15),
            comment='12 платежей, прошло 4',
            status='active',
        ),
        Debt(
            user_id=current_user.id,
            bank_name='Альфа-Банк',
            debt_type='credit_card',
            product_name='Альфа-Карта',
            total_amount=Decimal('50000'),
            remaining_amount=Decimal('8200'),
            minimum_payment=Decimal('1500'),
            interest_rate=Decimal('24.5'),
            next_payment_date=(today + timedelta(days=3)),
            comment='Почти погашена',
            status='active',
        ),
        Debt(
            user_id=current_user.id,
            bank_name='ВТБ',
            debt_type='split',
            product_name='ВТБ Части — iPhone 15',
            total_amount=Decimal('95000'),
            remaining_amount=Decimal('0'),
            minimum_payment=Decimal('0'),
            interest_rate=None,
            next_payment_date=None,
            comment='Полностью погашено',
            status='archived',
        ),
    ]

    for debt in debts:
        db.session.add(debt)
    db.session.flush()

    # Тестовые платежи для первого долга
    payments = [
        Payment(
            debt_id=debts[0].id,
            amount=Decimal('10000'),
            payment_date=previous_month_day(25, -1),
            comment='Плановый платеж',
            remaining_after_payment=Decimal('57500')
        ),
        Payment(
            debt_id=debts[0].id,
            amount=Decimal('20000'),
            payment_date=previous_month_day(25, -2),
            comment='Досрочный платеж',
            remaining_after_payment=Decimal('67500')
        ),
    ]
    for p in payments:
        db.session.add(p)

    db.session.commit()


# ──────────────────────────────────────────────────────────────
# Запуск приложения
# ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    from models import Debt, Payment  # Импортируем модели перед созданием таблиц
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
