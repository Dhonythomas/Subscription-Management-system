import re

from django.core.exceptions import ValidationError


class ComplexPasswordValidator:
    def validate(self, password, user=None):
        if len(password) <= 8:
            raise ValidationError("Password must be longer than 8 characters.")
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain an uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain a lowercase letter.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain a special character.")

    def get_help_text(self):
        return (
            "Your password must be longer than 8 characters and contain "
            "uppercase, lowercase, and special characters."
        )
