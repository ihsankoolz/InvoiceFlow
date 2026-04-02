import os

from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:password@bidding-db:3306/bidding_db")
