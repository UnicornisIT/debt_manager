# 💳 ДолгТрекер — Менеджер личных долгов

Веб-приложение для учёта кредитных карт и банковских сплитов с авторизацией через Telegram.

**Flask · MySQL · SQLAlchemy · Flask-Login · Bootstrap**

---

## ✨ Функциональность

| Функция | Описание |
|---------|----------|
| 🔐 Авторизация | Вход через Telegram Login Widget — без паролей |
| 👤 Мультипользователь | У каждого пользователя своя изолированная база долгов |
| 📊 Дашборд | Сводка: общий остаток, количество активных долгов, ближайший платёж, просроченные |
| 💳 Карточки | Кредитные карты и банковские сплиты с прогресс-баром погашения |
| 💸 Платежи | Внесение платежей с историей и автоматическим пересчётом остатка |
| 📁 Архив | Закрытые долги с возможностью восстановления или удаления |
| 🔍 Фильтры | Поиск по банку, фильтр по типу долга, сортировка |
| 🧾 Доходы и расходы | Учёт прихода и расхода с историей |
| 📊 Итоги месяца | Доходы, расходы, платежи по долгам и свободный остаток |
| 🎨 Тёмная тема | Цветная индикация статуса платежа |

### Цветовая индикация сроков

| Цвет | Значение |
|------|----------|
| 🟢 Зелёный | Платёж не скоро — более 7 дней |
| 🟡 Жёлтый | Скоро платёж — 3–7 дней |
| 🟠 Оранжевый | Платёж через 1–3 дня |
| 🔴 Красный | Просрочен |

---

## 📁 Структура проекта

```
debt_manager/
├── app.py              # Flask-приложение: роуты, API, аутентификация
├── models.py           # SQLAlchemy-модели (User, Debt, Payment)
├── extensions.py       # Объект db (SQLAlchemy)
├── config.py           # Конфигурация (из .env)
├── run.py              # Точка входа через Waitress (production)
├── init_db.sql         # SQL-скрипт создания БД
├── requirements.txt    # Зависимости Python
├── deploy.sh           # Скрипт деплоя на Linux-сервер
├── start.bat           # Быстрый запуск на Windows
├── .env.example        # Пример файла окружения
│
├── templates/
│   ├── base.html       # Базовый шаблон (навбар, модалки)
│   ├── login.html      # Страница входа (Telegram Widget)
│   ├── index.html      # Главный дашборд
│   ├── incomes.html    # Учёт доходов
│   ├── expenses.html   # Учёт расходов
│   └── archive.html    # Архив долгов
│
└── static/
    ├── css/style.css   # Стили (тёмная тема)
    └── js/app.js       # JavaScript (AJAX, модалки, фильтры)
```

---

## 🚀 Быстрый старт

### Требования

- Python 3.9+
- MySQL 8.0+
- Telegram-бот (для авторизации)

### 1. Клонировать репозиторий

```bash
git clone https://github.com/UnicornisIT/debt_manager.git
cd debt_manager
```

### 2. Виртуальное окружение и зависимости

В этом репозитории уже есть `.venv`, но вы можете создать своё виртуальное окружение.

```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Если вы используете другое имя папки, например `venv`, то активируйте соответствующий путь:

```bash
venv\Scripts\activate
# или
source venv/bin/activate
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
```

Откройте `.env` и заполните:

```env
SECRET_KEY=любая-случайная-строка

# Telegram-бот (обязателен для авторизации)
TELEGRAM_BOT_TOKEN=ваш_токен_бота
TELEGRAM_BOT_USERNAME=ваш_bot_username

# База данных
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=ваш_пароль
DB_NAME=debt_manager
```

> Токен бота получите у [@BotFather](https://t.me/BotFather). Для корректной работы Telegram Login Widget необходимо:
> - зарегистрировать домен вашего сайта в настройках бота через команду `/setdomain`
> - использовать HTTPS для доступа к приложению на сервере
> - указать в `.env` и в настройках домена тот же адрес, что будет использоваться в браузере
>
> Пример: если приложение доступно по `https://debt.example.com`, то именно этот домен должен быть разрешён в настройках бота.

### 4. Создать базу данных MySQL

```bash
mysql -u root -p < init_db.sql
```

Или интерактивно:

```sql
mysql -u root -p
SOURCE /путь/к/init_db.sql;
```

### 5. Запустить приложение

**Разработка:**
```bash
python app.py
```

**Production (через Waitress):**
```bash
python run.py
```

**Windows (всё в одном):**
```bat
start.bat
```

Откройте в браузере: **http://localhost:5000**

### 6. (Опционально) Загрузить тестовые данные

После входа через Telegram:

```bash
curl -X POST http://localhost:5000/api/init-db \
  -H "Cookie: session=<ваша_сессия>"
```

Тестовые данные добавляются только если у пользователя ещё нет ни одного долга.

---

## 🔐 Авторизация через Telegram

Приложение использует [Telegram Login Widget](https://core.telegram.org/widgets/login). При первом входе автоматически создаётся профиль пользователя. Данные сессии хранятся на стороне сервера через Flask-Login.

Важно: Telegram Login Widget работает только на разрешённых доменах и по HTTPS. Для настройки домена в BotFather выполните команду `/setdomain` и укажите домен без протокола, например `debt.example.com`.

В `templates/login.html` используется `data-auth-url`, который формирует ссылку на `https://<ваш-домен>/telegram-login`. Убедитесь, что этот адрес совпадает с реальным URL вашего сайта.

Подпись каждого запроса проверяется HMAC-SHA256 с ключом, производным от токена бота. Авторизационный токен действителен 24 часа.

---

## 🔌 REST API

Все эндпоинты требуют авторизации (сессионный cookie). Ответы возвращаются в формате JSON.

### Долги

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/api/debts` | Список долгов (параметры: `status`, `bank`, `type`) |
| `POST` | `/api/debts` | Создать долг |
| `GET` | `/api/debts/{id}` | Получить долг |
| `PUT` | `/api/debts/{id}` | Обновить долг |
| `POST` | `/api/debts/{id}/archive` | Переместить в архив |
| `POST` | `/api/debts/{id}/restore` | Восстановить из архива |
| `DELETE` | `/api/debts/{id}/delete` | Удалить безвозвратно |

### Платежи

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/api/debts/{id}/payments` | История платежей |
| `POST` | `/api/debts/{id}/payments` | Внести платёж |

### Пример — создание долга

```json
POST /api/debts
{
  "bank_name": "Тинькофф",
  "debt_type": "credit_card",
  "product_name": "Тинькофф Платинум",
  "total_amount": 85000,
  "remaining_amount": 47500,
  "minimum_payment": 3200,
  "interest_rate": 28.9,
  "next_payment_date": "2025-07-25",
  "comment": "Основная карта"
}
```

### Пример — внесение платежа

```json
POST /api/debts/1/payments
{
  "amount": 5000,
  "payment_date": "2025-07-10",
  "comment": "Плановый платёж"
}
```

---

## 🗄️ Модели данных

### User
| Поле | Тип | Описание |
|------|-----|----------|
| `telegram_id` | BigInteger | Уникальный ID пользователя в Telegram |
| `username` | String | @username |
| `first_name` / `last_name` | String | Имя и фамилия |
| `photo_url` | String | Аватар из Telegram |

### Debt
| Поле | Тип | Описание |
|------|-----|----------|
| `bank_name` | String | Название банка |
| `debt_type` | Enum | `credit_card` или `split` |
| `product_name` | String | Название продукта |
| `total_amount` | Decimal | Исходная сумма долга |
| `remaining_amount` | Decimal | Текущий остаток |
| `minimum_payment` | Decimal | Минимальный ежемесячный платёж |
| `interest_rate` | Decimal | Процентная ставка (для сплитов — null) |
| `next_payment_date` | Date | Дата следующего платежа |
| `status` | Enum | `active` или `archived` |

### Payment
| Поле | Тип | Описание |
|------|-----|----------|
| `amount` | Decimal | Сумма платежа |
| `payment_date` | Date | Дата платежа |
| `remaining_after_payment` | Decimal | Остаток долга после платежа |
| `comment` | Text | Комментарий |

---

## 🚢 Деплой на Linux-сервер

Приложение комплектуется скриптом `deploy.sh` для деплоя через systemd.

```bash
# На сервере в /var/www/debt_manager
bash deploy.sh
```

Скрипт выполняет: `git pull` → `pip install` → `db.create_all()` → `systemctl restart debt_manager`.

Пример конфигурации systemd-сервиса (`/etc/systemd/system/debt_manager.service`):

```ini
[Unit]
Description=Debt Manager Flask App
After=network.target mysql.service

[Service]
User=www-data
WorkingDirectory=/var/www/debt_manager
EnvironmentFile=/var/www/debt_manager/.env
ExecStart=/var/www/debt_manager/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🛠 Разработка

```bash
# Режим разработки с авто-перезагрузкой
FLASK_DEBUG=1 python app.py
```

Зависимости:

| Пакет | Версия | Назначение |
|-------|--------|------------|
| Flask | 3.0.3 | Веб-фреймворк |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| Flask-Login | 0.6.3 | Управление сессиями |
| PyMySQL | 1.1.1 | Драйвер MySQL |
| python-dotenv | 1.0.1 | Загрузка `.env` |
| waitress | 3.0.2 | WSGI-сервер для production |
| cryptography | 42.0.8 | Шифрование |
