"""
Django settings for myproject project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-0q8v+dbv==lfl3ha=efdm7a87^s#$@e4v!x4sr1r*3hqr&+hec'

DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '172.26.1.35',
    '172.20.10.5',
    '172.20.10.1',
    '10.0.2.2',
    '*',                    # временно для разработки
]
# ====================== CORS & CSRF (самая важная часть) ======================
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True
# Разрешаем запросы с вашего фронтенда
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://10.0.2.2:8000",
    "https://localhost:9000",  # Если используете HTTPS
    "http://127.0.0.1:8000",
    "http://172.28.20.54",  # ← добавьте ваш IP
]
# Дополнительно разрешаем методы и заголовки
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "content-type",
    "authorization",
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:8000',
    'http://10.0.2.2:8000',
    'http://172.26.1.35:8000',
    'http://172.28.20.54',
]

CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True

# ====================== APPLICATIONS ======================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'audio',
    'drf_spectacular',
    'django_filters',
    'django_celery_results',
    'corsheaders',
]

# ====================== MIDDLEWARE ======================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ====================== TEMPLATES ======================ss
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ====================== REST FRAMEWORK ======================
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ====================== AUTHENTICATION ======================
AUTHENTICATION_BACKENDS = [
    'audio.auth_backends.CommissionMemberAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ====================== SPECTACULAR ======================
SPECTACULAR_SETTINGS = {
    'TITLE': 'API Documentation',
    'DESCRIPTION': 'Система защиты проектов ИРНИТУ',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ====================== DATABASE ======================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',  # Имя вашей базы данных
        'USER': 'postgres',  # Имя пользователя PostgreSQL
        'PASSWORD': 'gfhjkmjncthdthf',  # Пароль пользователя
        'HOST': '127.0.0.1',  # Или IP-адрес вашего сервера
        'PORT': '5432',  # Порт PostgreSQL, по умолчанию 5432
    }
}

# ====================== CELERY ======================
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# ====================== STATIC & MEDIA ======================
STATIC_URL = '/static/'
#STATIC_ROOT = BASE_DIR/'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR/'media'
ROOT_URLCONF = 'myproject.urls'
# ====================== INTERNATIONALIZATION ======================
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Irkutsk'

USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ====================== PASSWORD HASHERS ======================
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]