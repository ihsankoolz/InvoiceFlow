CREATE DATABASE IF NOT EXISTS invoice_db;
USE invoice_db;

CREATE TABLE invoices (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) UNIQUE NOT NULL,
    seller_id       INT NOT NULL,
    debtor_name     VARCHAR(255),
    debtor_uen      VARCHAR(20) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    due_date        DATE NOT NULL,
    currency        VARCHAR(3) DEFAULT 'SGD',
    pdf_url         VARCHAR(500),
    status          ENUM('DRAFT', 'LISTED', 'FINANCED', 'REPAID', 'DEFAULTED', 'REJECTED') DEFAULT 'DRAFT',
    extracted_data  JSON,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
