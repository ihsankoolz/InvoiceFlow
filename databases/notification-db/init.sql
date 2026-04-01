CREATE DATABASE IF NOT EXISTS notification_db;
USE notification_db;

CREATE TABLE notifications (
    id          VARCHAR(36) PRIMARY KEY,
    user_id     INT NOT NULL,
    event_type  VARCHAR(100) NOT NULL,
    message     VARCHAR(500) NOT NULL,
    payload     JSON NOT NULL,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
