def luhn_check(imei: str) -> bool:
    """Validate IMEI using Luhn algorithm."""
    if not imei or not imei.isdigit() or len(imei) != 15:
        return False

    digits = [int(d) for d in imei]
    checksum = 0

    for i, digit in enumerate(digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled if doubled < 10 else doubled - 9
        else:
            checksum += digit

    return checksum % 10 == 0


def normalize_imei(value: str) -> str:
    """Clean IMEI / S/N input."""
    if not value:
        return ""
    return value.strip().replace(" ", "").replace("-", "").upper()


def is_valid_imei(value: str) -> bool:
    cleaned = normalize_imei(value)
    return len(cleaned) == 15 and cleaned.isdigit() and luhn_check(cleaned)


def generate_reference(year: int, sequence: int) -> str:
    """Generate unique reference: DZ-YYYY-XXXXXX"""
    return f"DZ-{year}-{sequence:06d}"
