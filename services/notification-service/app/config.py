import os
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "re_your_resend_api_key")
RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "notifications@invoiceflow.dev")
