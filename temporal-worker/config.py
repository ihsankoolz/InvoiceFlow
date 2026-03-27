import os
from dotenv import load_dotenv

load_dotenv()

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "temporal:7233")
INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://invoice-service:5001")
BIDDING_SERVICE_URL = os.getenv("BIDDING_SERVICE_URL", "http://bidding-service:5003")
MARKETPLACE_SERVICE_URL = os.getenv("MARKETPLACE_SERVICE_URL", "http://marketplace-service:5002")
PAYMENT_SERVICE_GRPC = os.getenv("PAYMENT_SERVICE_GRPC", "payment-service:50051")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
REPAYMENT_WINDOW_SECONDS = int(os.getenv("REPAYMENT_WINDOW_SECONDS", "86400"))
ANTI_SNIPE_SECONDS = int(os.getenv("ANTI_SNIPE_SECONDS", "300"))
