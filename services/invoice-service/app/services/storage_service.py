import io
from minio import Minio
from datetime import timedelta
from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET


class StorageService:
    """Handles PDF file storage and retrieval via MinIO (S3-compatible API)."""

    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,  # Set to True if using HTTPS
        )
        self.bucket = MINIO_BUCKET

    def _ensure_bucket_exists(self):
        """Creates the bucket if it does not already exist."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

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
        self._ensure_bucket_exists()
        object_name = f"{invoice_token}.pdf"
        
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(pdf_bytes),
            length=len(pdf_bytes),
            content_type="application/pdf",
        )
        
        # Return a simple internal identifier or URL
        return f"s3://{self.bucket}/{object_name}"

    def get_pdf_url(self, invoice_token: str) -> str:
        """Generate a presigned URL to access the stored PDF.

        Args:
            invoice_token: Unique token identifying the stored PDF object.

        Returns:
            A presigned URL string valid for temporary access.
        """
        object_name = f"{invoice_token}.pdf"
        # Generate a presigned URL valid for 1 hour
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            expires=timedelta(hours=1),
        )
