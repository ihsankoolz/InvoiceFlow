CREATE DATABASE IF NOT EXISTS bidding_db;
USE bidding_db;

CREATE TABLE bids (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) NOT NULL,
    investor_id     INT NOT NULL,
    bid_amount      DECIMAL(12,2) NOT NULL,
    status          ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED', 'OUTBID') DEFAULT 'PENDING',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_bid (invoice_token, investor_id)
);
