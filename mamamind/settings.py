import os
import sys
import io
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Force UTF-8 encoding for stdout/stderr
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-change-this')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
DEBUG_WHATSAPP = True

ALLOWED_HOSTS = ['*']  # Modify this for production

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'chatbot',
    'mealplanner',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mamamind.urls'

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

WSGI_APPLICATION = 'mamamind.wsgi.application'

# Database configuration for PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB_NAME', 'your_db_name'), 
        'USER': os.environ.get('POSTGRES_DB_USERNAME', 'your_db_user'),  
        'PASSWORD': os.environ.get('POSTGRES_DB_PASSWORD', 'your_db_password'),
        'HOST': os.environ.get('POSTGRES_DB_HOST', 'localhost'), 
        'PORT': os.environ.get('POSTGRES_DB_PORT', '5432'), 
    }
}

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# API Keys
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY', '')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Redis as message broker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # Store task results
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'  # WAT (UTC+1)
CELERY_ENABLE_UTC = False  # Use local time zone (WAT)

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'send-daily-tips': {
        'task': 'chatbot.tasks.send_scheduled_tasks',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM WAT daily
    },
    'send-daily-nudges': {
        'task': 'chatbot.tasks.send_scheduled_tasks',
        'schedule': crontab(hour=10, minute=0),  # 10:00 AM WAT daily
    },
    'send-weekly-meal-plans': {
        'task': 'chatbot.tasks.send_scheduled_tasks',
        'schedule': crontab(hour=8, minute=0, day_of_week='monday'),  # 8:00 AM WAT on Mondays
    },
}

# Site URL for Celery tasks
SITE_URL = 'http://localhost:8000'  # Update for production

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'meal_plan_debug.log',
            'encoding': 'utf-8',  # Explicitly set UTF-8 encoding
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    },
    'loggers': {
        'chatbot.utils.sonar': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}