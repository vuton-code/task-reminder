"""Tests only connect to a separate database on the local development server."""
from .settings import *
from django.core.exceptions import ImproperlyConfigured

if not DEBUG or DATABASES["default"].get("HOST") not in {"localhost","127.0.0.1","::1","db"}:
    raise ImproperlyConfigured("Tests require the local development PostgreSQL server with DEBUG=true.")
if DATABASES["default"]["NAME"]=="test_task_reminder":
    raise ImproperlyConfigured("DATABASE_URL must name the development database, never the test database.")
DATABASES["default"]["TEST"]={"NAME":"test_task_reminder"}
EMAIL_BACKEND_MODE="fake"
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
RESEND_API_KEY=""
RESEND_WEBHOOK_SECRET=""
