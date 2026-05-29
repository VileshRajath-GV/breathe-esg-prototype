
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


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'config.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

CORS_ALLOW_ALL_ORIGINS = True
