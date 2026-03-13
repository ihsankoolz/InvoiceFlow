class PDFExtractor:
    """Extracts structured fields from invoice PDF documents using pdfplumber."""

    def extract_fields(self, pdf_bytes: bytes) -> dict:
        """Parse the given PDF bytes and extract invoice-relevant fields.

        Uses pdfplumber to read pages, extract text, and attempt to identify
        common invoice fields such as invoice number, dates, line items, and totals.

        Args:
            pdf_bytes: Raw bytes of the PDF file.

        Returns:
            A dictionary of extracted field names to their values.
        """
        # TODO: implement using pdfplumber
        raise NotImplementedError
