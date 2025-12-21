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
    'drf_spectacular',
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
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
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

# Google Gemini API Configuration
GEMINI_API_KEY = config('GEMINI_API_KEY', default=None)
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-3-flash-preview')
GEMINI_ENABLED = config('GEMINI_ENABLED', default=True, cast=bool)
GEMINI_MAX_TEXT_LENGTH = config('GEMINI_MAX_TEXT_LENGTH', default=50000, cast=int)
GEMINI_TIMEOUT = config('GEMINI_TIMEOUT', default=30, cast=int)

# Swagger/OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'ZapSign API',
    'DESCRIPTION': '''
    API para gerenciamento de documentos e assinaturas digitais.
    
    ## Funcionalidades Principais
    
    - **Gerenciamento de Documentos**: Criação, listagem, atualização e exclusão de documentos
    - **Análise com IA**: Análise inteligente de documentos usando spaCy e Google Gemini
    - **Assinatura Digital**: Integração com provedores de assinatura digital (ZapSign)
    - **Gerenciamento de Signatários**: Adição e acompanhamento de signatários
    - **Webhooks**: Recebimento de eventos dos provedores de assinatura
    - **Métricas e Alertas**: Monitoramento de documentos e alertas importantes
    
    ## Autenticação
    
    A API utiliza autenticação por Token. Para obter um token:
    
    1. Faça uma requisição POST para `/api/api-token-auth/` com `username` e `password`
    2. Use o token retornado no header: `Authorization: Token <seu-token>`
    
    ## Códigos de Status HTTP
    
    - `200 OK`: Requisição bem-sucedida
    - `201 Created`: Recurso criado com sucesso
    - `400 Bad Request`: Erro na requisição (validação, dados inválidos)
    - `401 Unauthorized`: Token de autenticação inválido ou ausente
    - `404 Not Found`: Recurso não encontrado
    - `500 Internal Server Error`: Erro interno do servidor
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'ZapSign API Support',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    'TAGS': [
        {'name': 'Autenticação', 'description': 'Endpoints para autenticação e obtenção de tokens'},
        {'name': 'Providers', 'description': 'Gerenciamento de provedores de assinatura digital'},
        {'name': 'Companies', 'description': 'Gerenciamento de empresas e configurações'},
        {'name': 'Documents', 'description': 'Gerenciamento de documentos, análise com IA e operações de assinatura'},
        {'name': 'Signers', 'description': 'Gerenciamento de signatários de documentos'},
        {'name': 'Webhooks', 'description': 'Endpoints para recebimento de webhooks dos provedores'},
        {'name': 'Health', 'description': 'Endpoints de verificação de saúde da API'},
    ],
    'AUTHENTICATION_WHITELIST': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Servidor de desenvolvimento'},
    ],
    'SCHEMA_PATH_PREFIX': '/api/',
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 1,
        'defaultModelExpandDepth': 1,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'hideSingleRequestSample': False,
        'expandResponses': '200,201',
        'pathInMiddlePanel': True,
        'requiredPropsFirst': True,
        'sortOperationsAlphabetically': False,
        'sortTagsAlphabetically': True,
    },
}

