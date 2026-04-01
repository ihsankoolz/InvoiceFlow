import os

DB_URL: str = os.getenv("DB_URL", "mysql+pymysql://root:password@user-db:3306/user_db")
JWT_SECRET: str = os.getenv("JWT_SECRET", "your-jwt-secret-change-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
