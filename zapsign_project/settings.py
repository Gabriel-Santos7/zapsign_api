from pathlib import Path
from decouple import config
import os
import logging

BASE_DIR = Path(__file__).resolve().parent.parent

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

allowed_hosts_env = config('ALLOWED_HOSTS', default=None)
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',')]
elif not DEBUG:
    # Em produção: inclui domínio do Render
    ALLOWED_HOSTS = ['zapsign-api.onrender.com', '*']
else:
    # Desenvolvimento: localhost e domínio do Render (para testes)
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'zapsign-api.onrender.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'apps.domain',
    'apps.application',
    'apps.infrastructure',
    'apps.presentation',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zapsign_project.urls'

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

WSGI_APPLICATION = 'zapsign_project.wsgi.application'

# Configuração do banco de dados
# Render fornece DATABASE_URL, Docker Compose usa variáveis individuais
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Render ou outros serviços que fornecem DATABASE_URL
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
        }
    except ImportError:
        # Fallback se dj-database-url não estiver instalado
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': config('POSTGRES_DB', default='zapsign_db'),
                'USER': config('POSTGRES_USER', default='zapsign_user'),
                'PASSWORD': config('POSTGRES_PASSWORD', default='zapsign_pass'),
                'HOST': config('DB_HOST', default='db'),
                'PORT': config('DB_PORT', default='5432'),
            }
        }
else:
    # Docker Compose ou desenvolvimento local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB', default='zapsign_db'),
            'USER': config('POSTGRES_USER', default='zapsign_user'),
            'PASSWORD': config('POSTGRES_PASSWORD', default='zapsign_pass'),
            'HOST': config('DB_HOST', default='db'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

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

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# CORS Configuration - Permitir todas as origens temporariamente
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Log para debug
print('[CORS] CORS_ALLOW_ALL_ORIGINS = True (permitindo todas as origens)')
logger = logging.getLogger(__name__)
logger.info('CORS_ALLOW_ALL_ORIGINS = True (permitindo todas as origens)')

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_PREFLIGHT_MAX_AGE = 86400

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
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
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

ZAPSIGN_SANDBOX_URL = config('ZAPSIGN_SANDBOX_URL', default='https://sandbox.api.zapsign.com.br')
ZAPSIGN_PRODUCTION_URL = config('ZAPSIGN_PRODUCTION_URL', default='https://api.zapsign.com.br')

# Document Analysis Configuration
SPACY_MODEL = config('SPACY_MODEL', default='pt_core_news_lg')
ANALYSIS_SUMMARY_LENGTH = config('ANALYSIS_SUMMARY_LENGTH', default=5, cast=int)

