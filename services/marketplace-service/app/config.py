import os

DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:password@market-db:3306/market_db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
