-- ============================================================
-- Скрипт создания базы данных debt_manager
-- Выполните этот скрипт в MySQL перед запуском приложения
-- ============================================================

CREATE DATABASE IF NOT EXISTS debt_manager
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE debt_manager;

-- Таблица пользователей для Telegram-авторизации
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(80) NULL,
    first_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NULL,
    photo_url VARCHAR(255) NULL,
    auth_date DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица долгов
CREATE TABLE IF NOT EXISTS debts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    bank_name       VARCHAR(100)    NOT NULL COMMENT 'Название банка',
    debt_type       ENUM('credit_card', 'split') NOT NULL COMMENT 'Тип: кредитная карта или сплит',
    product_name    VARCHAR(150)    NOT NULL COMMENT 'Название продукта/карты',
    total_amount    DECIMAL(12, 2)  NOT NULL COMMENT 'Первоначальная сумма долга',
    remaining_amount DECIMAL(12, 2) NOT NULL COMMENT 'Текущий остаток долга',
    minimum_payment DECIMAL(12, 2)  NULL     COMMENT 'Минимальный ежемесячный платеж',
    interest_rate   DECIMAL(5, 2)   NULL     COMMENT 'Процентная ставка в год',
    next_payment_date DATE          NULL     COMMENT 'Дата следующего платежа',
    comment         TEXT            NULL     COMMENT 'Комментарий',
    status          ENUM('active', 'archived') NOT NULL DEFAULT 'active' COMMENT 'Статус',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_next_payment (next_payment_date),
    INDEX idx_bank (bank_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Таблица платежей
CREATE TABLE IF NOT EXISTS payments (
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    debt_id                  INT             NOT NULL COMMENT 'ID долга',
    amount                   DECIMAL(12, 2)  NOT NULL COMMENT 'Сумма платежа',
    payment_date             DATE            NOT NULL COMMENT 'Дата платежа',
    comment                  TEXT            NULL     COMMENT 'Комментарий к платежу',
    remaining_after_payment  DECIMAL(12, 2)  NOT NULL COMMENT 'Остаток долга после платежа',
    created_at               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (debt_id) REFERENCES debts(id) ON DELETE CASCADE,
    INDEX idx_debt_id (debt_id),
    INDEX idx_payment_date (payment_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
