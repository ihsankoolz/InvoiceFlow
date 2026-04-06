import os

from dotenv import load_dotenv

load_dotenv()

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
ACRA_WRAPPER_URL = os.getenv("ACRA_WRAPPER_URL", "http://acra-wrapper:5007")
