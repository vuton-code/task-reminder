import pytest
from cryptography.fernet import Fernet

@pytest.fixture(autouse=True)
def isolated_settings(settings):
    settings.DEBUG = True
    settings.EMAIL_BACKEND_MODE = "fake"
    settings.OUTBOX_ENCRYPTION_KEY = Fernet.generate_key().decode()
    settings.SECURE_SSL_REDIRECT = False
