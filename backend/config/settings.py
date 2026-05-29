
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'dev'
DEBUG = True
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CORS_ALLOW_ALL_ORIGINS = True
