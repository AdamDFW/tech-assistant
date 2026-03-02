import re

VIN_RE = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b")  # VIN excludes I,O,Q

def normalize_vin(vin: str) -> str:
    """Uppercase, strip spaces/dashes, keep alphanumerics only."""
    if not vin:
        return ""
    vin = vin.strip().upper()
    vin = re.sub(r"[^A-Z0-9]", "", vin)
    return vin

def last6_from_vin(vin: str) -> str:
    vin = normalize_vin(vin)
    return vin[-6:] if len(vin) >= 6 else ""

def find_vins_in_text(text: str) -> list[str]:
    """Return any 17-char VIN-like tokens found in text."""
    if not text:
        return []
    text = text.upper()
    return list({m.group(1) for m in VIN_RE.finditer(text)})

# ---- Future hook (AI/OCR later) ----
def ocr_vin_from_image_bytes(image_bytes: bytes) -> dict:
    """
    Placeholder: later replace with OCR/AI.
    Return shape:
      {"vin": "....", "confidence": 0.92, "source": "ocr"}
    """
    return {"vin": "", "confidence": 0.0, "source": "ocr"}