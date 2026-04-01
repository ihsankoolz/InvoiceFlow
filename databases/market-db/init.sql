CREATE DATABASE IF NOT EXISTS market_db;
USE market_db;

CREATE TABLE listings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) UNIQUE NOT NULL,
    seller_id       INT NOT NULL,
    debtor_uen      VARCHAR(20) NOT NULL,
    -- original columns
    amount          DECIMAL(12,2) NOT NULL,
    minimum_bid     DECIMAL(12,2) NOT NULL,
    urgency_level   ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    deadline        DATETIME NOT NULL,
    status          ENUM('ACTIVE', 'CLOSED', 'EXPIRED') DEFAULT 'ACTIVE',
    -- read-model columns (populated by event consumer / listing creation)
    face_value      DECIMAL(12,2) NULL,
    debtor_name     VARCHAR(255) NULL,
    current_bid     DECIMAL(12,2) NULL,
    bid_count       INT NOT NULL DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
