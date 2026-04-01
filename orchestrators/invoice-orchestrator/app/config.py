import os

from dotenv import load_dotenv

load_dotenv()

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://invoice-service:5001")
MARKETPLACE_SERVICE_URL = os.getenv("MARKETPLACE_SERVICE_URL", "http://marketplace-service:5002")
ACRA_WRAPPER_URL = os.getenv("ACRA_WRAPPER_URL", "http://acra-wrapper:5007")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "temporal:7233")
