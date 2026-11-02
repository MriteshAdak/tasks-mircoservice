"""Business-rule validators for user registration."""

import re

from users_api.exceptions import ValidationException


_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9_.-]{1,62}[a-zA-Z0-9])?$")


def validate_username(username: str) -> None:
    """Require a stable, URL-safe username between 3 and 64 characters."""

    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValidationException(
            "Username must be 3-64 characters and use only letters, digits, '.', '_' or '-'."
        )


def validate_display_name(display_name: str) -> None:
    """Require a non-blank display name no longer than 100 characters."""

    if not display_name.strip() or len(display_name) > 100:
        raise ValidationException("Display name must contain 1-100 non-blank characters.")


def validate_password(password: str) -> None:
    """Require a suitably strong local-development password."""

    if len(password) < 12 or len(password) > 128:
        raise ValidationException("Password must be between 12 and 128 characters.")
    if not any(character.islower() for character in password):
        raise ValidationException("Password must include a lowercase letter.")
    if not any(character.isupper() for character in password):
        raise ValidationException("Password must include an uppercase letter.")
    if not any(character.isdigit() for character in password):
        raise ValidationException("Password must include a digit.")
    if not any(not character.isalnum() for character in password):
        raise ValidationException("Password must include a special character.")
