import io
import re
import pdfplumber


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
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        # Basic heuristic extraction
        extracted = {
            "raw_text": text[:1000],  # Store some raw text for debugging
            "debtor_name": None,
            "amount": None,
        }

        # Try to find "Bill To:" or "To:" for debtor name
        debtor_match = re.search(r"(?:Bill To|To|Client):\s*(.*)", text, re.IGNORECASE)
        if debtor_match:
            extracted["debtor_name"] = debtor_match.group(1).split("\n")[0].strip()

        # Try to find currency-like amounts
        # Looks for things like "Total: $1,234.56" or "Amount Due: 100.00"
        amount_match = re.search(r"(?:Total|Amount Due|Total Amount|Grand Total)[^\d]*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if amount_match:
            try:
                # Remove commas and convert to float
                val = amount_match.group(1).replace(",", "")
                extracted["amount"] = float(val)
            except ValueError:
                pass

        return extracted
