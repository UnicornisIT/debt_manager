# 💳 ДолгТрекер — Менеджер личных долгов

Веб-приложение для учёта кредитных карт и банковских сплитов.  
**Flask + MySQL + SQLAlchemy + Bootstrap**

---

## 📁 Структура проекта

```
debt_manager/
├── app.py              # Flask-приложение: роуты и API
├── models.py           # SQLAlchemy-модели (Debt, Payment)
├── extensions.py       # Объект db (SQLAlchemy)
├── config.py           # Конфигурация (из .env)
├── init_db.sql         # SQL-скрипт создания БД
├── requirements.txt    # Зависимости Python
├── .env.example        # Пример файла окружения
│
├── templates/
│   ├── base.html       # Базовый шаблон (навбар, модалки)
│   ├── index.html      # Главный дашборд
│   └── archive.html    # Архив долгов
│
└── static/
    ├── css/
    │   └── style.css   # Все стили (тёмная тема)
    └── js/
        └── app.js      # JavaScript (AJAX, модалки, фильтры)
```

---

## 🚀 Быстрый старт

### 1. Клонируйте или распакуйте проект

```bash
cd debt_manager
```

### 2. Создайте виртуальное окружение и установите зависимости

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Настройте файл окружения

```bash
cp .env.example .env
```

Откройте `.env` и заполните:
```
SECRET_KEY=любая-случайная-строка
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=ваш_пароль
DB_NAME=debt_manager
```

### 4. Создайте базу данных MySQL

Войдите в MySQL:
```bash
mysql -u root -p
```

Выполните SQL-скрипт:
```sql
SOURCE /путь/к/init_db.sql;
```

Или через командную строку:
```bash
mysql -u root -p < init_db.sql
```

### 5. Запустите приложение

```bash
python app.py
```

Откройте в браузере: **http://localhost:5000**

### 6. (Опционально) Загрузите тестовые данные

```bash
curl -X POST http://localhost:5000/api/init-db
```

Или через браузер откройте: `http://localhost:5000/api/init-db` (POST-запрос через curl/Postman).

---

## ✨ Функционал

| Функция | Описание |
|---------|----------|
| 📊 Дашборд | Сводка по всем активным долгам |
| 💳 Карточки | Кредитные карты и сплиты |
| 💸 Платежи | Внесение платежей с историей |
| 📁 Архив | Закрытые долги с возможностью восстановления |
| 🗓️ Calendar | Интеграция с Google Calendar |
| 🔍 Фильтры | Поиск, фильтр по типу, сортировка |
| 🎨 UI | Тёмная тема, цветная индикация статуса |

### Цветовая индикация:
- 🟢 **Зелёный** — платеж не скоро (>7 дней)  
- 🟡 **Жёлтый** — скоро платеж (3–7 дней)  
- 🟠 **Оранжевый** — платеж через 1–3 дня  
- 🔴 **Красный** — просрочен  

---

## 🔌 API-эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/debts` | Список долгов |
| POST | `/api/debts` | Создать долг |
| GET | `/api/debts/{id}` | Получить долг |
| PUT | `/api/debts/{id}` | Обновить долг |
| POST | `/api/debts/{id}/archive` | Архивировать |
| POST | `/api/debts/{id}/restore` | Восстановить |
| DELETE | `/api/debts/{id}/delete` | Удалить |
| GET | `/api/debts/{id}/payments` | История платежей |
| POST | `/api/debts/{id}/payments` | Внести платеж |

---

## 📋 Требования

- Python 3.9+
- MySQL 8.0+
- Современный браузер (Chrome, Firefox, Safari, Edge)

---

## 🛠 Разработка

```bash
# Запуск в режиме разработки (с авто-перезагрузкой)
FLASK_ENV=development python app.py
```
