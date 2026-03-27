import os

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_your_stripe_secret_key")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/payment/success")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/payment/cancel")
