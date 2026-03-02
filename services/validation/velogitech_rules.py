from services.vin_service import normalize_vin, last6_from_vin

def validate_velogitech(work_order: dict) -> list[dict]:
    """
    Returns list of issues:
      [{"level":"error|warn", "code":"...", "message":"..."}]
    """
    issues = []

    vin = normalize_vin(work_order.get("vin", ""))
    last6 = (work_order.get("vin_last6", "") or "").strip().upper()

    # Required: VIN plate photo
    photos = work_order.get("photos", [])
    has_vin_plate = any(p.get("type") == "vin_plate" for p in photos)
    if not has_vin_plate:
        issues.append({
            "level": "error",
            "code": "VIN_PLATE_PHOTO_MISSING",
            "message": "VIN plate photo is required."
        })

    # Required: last6 verification
    if not last6:
        issues.append({
            "level": "error",
            "code": "VIN_LAST6_MISSING",
            "message": "Verification (last 6 of VIN) is required."
        })

    # Consistency check (warn)
    if vin and last6 and last6 != last6_from_vin(vin):
        issues.append({
            "level": "warn",
            "code": "VIN_LAST6_MISMATCH",
            "message": f"Last 6 '{last6}' does not match VIN last 6 '{last6_from_vin(vin)}'."
        })

    return issues