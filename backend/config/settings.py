
from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'corsheaders',
    'tenants',
    'ingestion',
    'emissions',
    'reviews',
]

# Custom user model (role-based, tenant-scoped)
AUTH_USER_MODEL = 'tenants.ESGUser'

# Suppress auto-field system check warnings
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ─── Database ────────────────────────────────────────────────────────────────
# On Render: DATABASE_URL is injected automatically by the linked PostgreSQL service.
# Locally: falls back to SQLite so dev setup requires no extra config.

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Production — PostgreSQL on Render
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,        # persistent connections
            conn_health_checks=True,
        )
    }
else:
    # Local development — SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

CORS_ALLOW_ALL_ORIGINS = True
