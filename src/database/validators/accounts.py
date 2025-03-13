import re

import email_validator


def validate_password_strength(password: str) -> str:
    if any(not re.search(pattern, password) for pattern in [
        r".{8,}",
        r"[A-Z]",
        r"[a-z]",
        r"\d",
        r"[@$!%*?&#]"
    ]):
        raise ValueError(
            "Password must be at least 8 characters long "
            "and contain an uppercase letter, "
            "a lowercase letter, a digit, and a "
            "special character (@, $, !, %, *, ?, #, &)."
        )
    return password


def validate_email(user_email: str) -> str:
    try:
        email_info = email_validator.validate_email(
            user_email, check_deliverability=False
        )
        email = email_info.normalized
    except email_validator.EmailNotValidError as error:
        raise ValueError(str(error))
    else:
        return email
