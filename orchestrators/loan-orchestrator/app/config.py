import os

from dotenv import load_dotenv

load_dotenv()

PAYMENT_SERVICE_GRPC = os.getenv("PAYMENT_SERVICE_GRPC", "payment-service:50051")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
STRIPE_WRAPPER_URL = os.getenv("STRIPE_WRAPPER_URL", "http://stripe-wrapper:5008")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:5004")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
