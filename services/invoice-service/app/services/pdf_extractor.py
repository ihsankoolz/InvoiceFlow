import io
import re
from datetime import datetime

import pdfplumber


class PDFExtractor:
    """Extracts structured fields from invoice PDF documents using pdfplumber."""

    def extract_fields(self, pdf_bytes: bytes) -> dict:
        extracted = {
            "raw_text": "",
            "debtor_name": None,
            "debtor_uen": None,
            "amount": None,
            "due_date": None,
        }

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                return extracted

            page = pdf.pages[0]
            full_text = page.extract_text() or ""
            extracted["raw_text"] = full_text[:1000]

            # ── Locate "BILL TO" by word coordinates ──────────────────────────
            words = page.extract_words()
            bill_to_x = None
            bill_to_y = None
            for i, w in enumerate(words):
                if w["text"].upper() == "BILL":
                    for j in range(i + 1, min(i + 3, len(words))):
                        if words[j]["text"].upper() == "TO" and abs(words[j]["top"] - w["top"]) < 5:
                            bill_to_x = w["x0"]
                            bill_to_y = w["top"]
                            break
                if bill_to_x is not None:
                    break

            # ── Crop to BILL TO column, extract debtor name + UEN ─────────────
            if bill_to_x is not None:
                # Crop: from BILL TO's x-pos to right edge, top 55% of page
                crop = page.crop((bill_to_x, bill_to_y, page.width, page.height * 0.55))
                bill_to_text = crop.extract_text() or ""

                lines = [line.strip() for line in bill_to_text.split("\n") if line.strip()]
                for line in lines:
                    upper = line.upper()
                    if upper in ("BILL TO", "BILL", "TO"):
                        continue
                    if upper.startswith("UEN"):
                        continue
                    # Skip obvious address lines
                    if re.match(r"^\d+\s", line) or "@" in line or line.startswith("+"):
                        continue
                    extracted["debtor_name"] = line
                    break

                uen_match = re.search(r"UEN[:\s]*([A-Z0-9]{9,10})\b", bill_to_text, re.IGNORECASE)
                if uen_match:
                    extracted["debtor_uen"] = uen_match.group(1).strip().upper()

            # Fallback for debtor name if coordinate crop didn't work
            if not extracted["debtor_name"]:
                m = re.search(r"(?:Bill To|To|Client):\s*(.+)", full_text, re.IGNORECASE)
                if m:
                    extracted["debtor_name"] = m.group(1).strip()

            # ── Due date ──────────────────────────────────────────────────────
            due_match = re.search(
                r"Due\s+Date[:\s]*([\d]{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
                full_text,
                re.IGNORECASE,
            )
            if due_match:
                raw_date = due_match.group(1).strip()
                for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        extracted["due_date"] = datetime.strptime(raw_date, fmt).strftime(
                            "%Y-%m-%d"
                        )
                        break
                    except ValueError:
                        continue

            # ── Amount ────────────────────────────────────────────────────────
            amount_match = re.search(r"Face\s+Value[^\d]*([\d,]+\.?\d*)", full_text, re.IGNORECASE)
            if not amount_match:
                amount_match = re.search(
                    r"(?:Total\s+Due|Amount\s+Due|Grand\s+Total|Total\s+Amount|Total)[^\d]*([\d,]+\.?\d*)",
                    full_text,
                    re.IGNORECASE,
                )
            if amount_match:
                try:
                    extracted["amount"] = float(amount_match.group(1).replace(",", ""))
                except ValueError:
                    pass

        return extracted
