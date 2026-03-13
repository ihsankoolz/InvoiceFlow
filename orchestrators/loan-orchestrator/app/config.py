import os
from dotenv import load_dotenv

load_dotenv()

PAYMENT_SERVICE_GRPC = os.getenv("PAYMENT_SERVICE_GRPC", "payment-service:50051")
STRIPE_WRAPPER_URL = os.getenv("STRIPE_WRAPPER_URL", "http://stripe-wrapper:5008")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672")
