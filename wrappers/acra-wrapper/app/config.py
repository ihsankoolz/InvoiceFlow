import os

DATA_GOV_API_URL = os.getenv("DATA_GOV_API_URL", "https://data.gov.sg/api/action/datastore_search")
ACRA_DATASET_RESOURCE_ID = os.getenv(
    "ACRA_DATASET_RESOURCE_ID", "d_3f960c10fed6145404ca7b821f263b87"
)
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
MOCK_UEN_VALIDATION = os.getenv("MOCK_UEN_VALIDATION", "false").lower() == "true"
