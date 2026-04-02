import os

from dotenv import load_dotenv

load_dotenv()

BIDDING_SERVICE_URL = os.getenv("BIDDING_SERVICE_URL", "http://bidding-service:5003")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
MARKETPLACE_SERVICE_URL = os.getenv("MARKETPLACE_SERVICE_URL", "http://marketplace-service:5002")
INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://invoice-service:5001")
STRIPE_WRAPPER_URL = os.getenv("STRIPE_WRAPPER_URL", "http://stripe-wrapper:5008")
PAYMENT_SERVICE_GRPC = os.getenv("PAYMENT_SERVICE_GRPC", "payment-service:50051")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:5004")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "temporal:7233")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")
