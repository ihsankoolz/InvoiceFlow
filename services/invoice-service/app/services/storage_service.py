from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET


class StorageService:
    """Handles PDF file storage and retrieval via MinIO (S3-compatible API)."""

    def __init__(self):
        self.endpoint = MINIO_ENDPOINT
        self.access_key = MINIO_ACCESS_KEY
        self.secret_key = MINIO_SECRET_KEY
        self.bucket = MINIO_BUCKET

    def upload_pdf(self, invoice_token: str, pdf_bytes: bytes) -> str:
        """Upload a PDF file to MinIO under the given invoice token.

        The object is stored as ``<invoice_token>.pdf`` inside the configured bucket.
        Creates the bucket if it does not already exist.

        Args:
            invoice_token: Unique token used as the object name prefix.
            pdf_bytes: Raw bytes of the PDF file.

        Returns:
            The object URL string for the uploaded PDF.
        """
        # TODO: implement using minio client
        raise NotImplementedError

    def get_pdf_url(self, invoice_token: str) -> str:
        """Generate a presigned URL to access the stored PDF.

        Args:
            invoice_token: Unique token identifying the stored PDF object.

        Returns:
            A presigned URL string valid for temporary access.
        """
        # TODO: implement using minio client presigned_get_object
        raise NotImplementedError
