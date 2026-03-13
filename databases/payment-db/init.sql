CREATE DATABASE IF NOT EXISTS payment_db;
USE payment_db;

CREATE TABLE wallets (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNIQUE NOT NULL,
    balance         DECIMAL(12,2) DEFAULT 0.00,
    currency        VARCHAR(3) DEFAULT 'SGD',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE escrows (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    investor_id     INT NOT NULL,
    invoice_token   VARCHAR(36) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    status          ENUM('LOCKED', 'CONVERTED', 'RELEASED') DEFAULT 'LOCKED',
    idempotency_key VARCHAR(100) UNIQUE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_escrow (investor_id, invoice_token)
);

CREATE TABLE loans (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    loan_id         VARCHAR(36) UNIQUE NOT NULL,
    invoice_token   VARCHAR(36) NOT NULL,
    investor_id     INT NOT NULL,
    seller_id       INT NOT NULL,
    principal       DECIMAL(12,2) NOT NULL,
    penalty_amount  DECIMAL(12,2) DEFAULT 0.00,
    status          ENUM('ACTIVE', 'DUE', 'REPAID', 'OVERDUE') DEFAULT 'ACTIVE',
    due_date        DATE NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
