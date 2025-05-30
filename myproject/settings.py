"""
Django settings for myproject project.

Generated by 'django-admin startproject' using Django 5.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-0q8v+dbv==lfl3ha=efdm7a87^s#$@e4v!x4sr1r*3hqr&+hec'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


# settings.py
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '10.0.2.2', '0.0.0.0', '172.20.10.5', '172.20.10.1']
# Разрешить доступ с любых хостов при DEBUG (только для разработки!)
if DEBUG:
    ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'audio',
    'drf_spectacular',
    'django_filters',
    'django_celery_results',
    'corsheaders',  # Добавьте это
]

# Настройки документации
SPECTACULAR_SETTINGS = {
    'TITLE': 'API Documentation',
    'DESCRIPTION': 'Основные методы я тут выкладываю',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',  # Если API начинается с /api/
}

REST_FRAMEWORK = {
    # ... другие настройки DRF ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Должн
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

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

WSGI_APPLICATION = 'myproject.wsgi.application'

CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'Dip',  # Имя вашей базы данных
        'USER': 'postgres',  # Имя пользователя PostgreSQL
        'PASSWORD': '1',  # Пароль пользователя
        'HOST': 'localhost',  # Или IP-адрес вашего сервера
        'PORT': '5432',  # Порт PostgreSQL, по умолчанию 5432
    }
}



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Или явно укажите разрешенные адреса:
CORS_ALLOWED_ORIGINS = [
    "http://172.20.10.5:8000",
    "http://172.20.10.1:8000",  # Ваш IP
    "https://localhost:9000",  # Если используете HTTPS
    "http://localhost:9000",
]


# Разрешаем запросы с вашего фронтенда
CORS_ALLOWED_ORIGINS = [
    "http://localhost:9000",
    "https://localhost:9000",  # Если используете HTTPS
]

# Дополнительно разрешаем методы и заголовки
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "OPTIONS",  # Важно для preflight-запросов
]

CORS_ALLOW_HEADERS = [
    "accept",
    "content-type",
    "authorization",
]

# Настройки для Bitrix
BITRIX_CLIENT_ID = "local.65581f0597f2b3.73164583"
BITRIX_SECRET_KEY = "9FTLONYzoMlenvlQBm1TUTfRf1x7ZAUtJK948jeyM2mGmvH0z7"