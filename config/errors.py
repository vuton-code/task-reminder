from django.core.exceptions import ValidationError

class Conflict(ValidationError):
    pass
