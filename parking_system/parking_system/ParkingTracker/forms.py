from typing import Dict, List


def validate_registration(data: Dict[str, str]) -> List[str]:
    errors = []
    if not data.get("full_name", "").strip():
        errors.append("Full name is required.")
    if not data.get("email", "").strip() or "@" not in data.get("email", ""):
        errors.append("Please provide a valid email address.")
    if len(data.get("password", "")) < 6:
        errors.append("Password must be at least 6 characters.")
    if data.get("password") != data.get("confirm_password"):
        errors.append("Passwords do not match.")
    return errors


def validate_login(data: Dict[str, str]) -> List[str]:
    errors = []
    if not data.get("email", "").strip():
        errors.append("Email is required.")
    if not data.get("password", ""):
        errors.append("Password is required.")
    return errors
