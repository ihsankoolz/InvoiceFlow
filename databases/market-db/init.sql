CREATE DATABASE IF NOT EXISTS market_db;
USE market_db;

CREATE TABLE listings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) UNIQUE NOT NULL,
    seller_id       INT NOT NULL,
    debtor_uen      VARCHAR(20) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    urgency_level   ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    deadline        DATETIME NOT NULL,
    status          ENUM('ACTIVE', 'CLOSED', 'EXPIRED') DEFAULT 'ACTIVE',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
