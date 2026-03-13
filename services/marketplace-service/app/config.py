import os

DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:password@market-db:3306/market_db")
