"""
Django settings for x project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
from decouple import config
import redis
import psycopg2
from datetime import timedelta
import base64

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def decipher(value):
    return base64.b64decode(value.encode()).decode()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'g7+b)g5r@ugo4&ix$mto0b(u*^9_51p5a5-j#_@t)1g!fv&j99'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

DEPLOYMENT_INSTANCE = config('DEPLOYMENT_INSTANCE', default='local')

ALLOWED_HOSTS = [
    'watchtower.scibizinformatics.com',
    'localhost',
    '*'
]

# Application definition

INSTALLED_APPS=[
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django.contrib.admin',
    'drf_yasg',
    'channels',
    'main',
]

MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'watchtower.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'watchtower.wsgi.application'
ASGI_APPLICATION = 'watchtower.asgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

POSTGRES_DB = decipher(config('POSTGRES_DB'))
POSTGRES_HOST = decipher(config('POSTGRES_HOST'))
POSTGRES_PORT = decipher(config('POSTGRES_PORT'))
POSTGRES_USER = decipher(config('POSTGRES_USER'))
POSTGRES_PASSWORD = decipher(config('POSTGRES_PASSWORD'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': POSTGRES_DB,
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        # 'OPTIONS': {
        #     'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
        # }
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DB_NUM = [0,1,2]
if DEPLOYMENT_INSTANCE == 'staging':
    DB_NUM = [3,4,5]

REDIS_HOST = decipher(config('REDIS_HOST', default='localhost'))
REDIS_PASSWORD = decipher(config('REDIS_PASSWORD', default=''))
REDIS_PORT = decipher(config('REDIS_PORT', default=6379))
CELERY_IMPORTS = ('main.tasks',)

if REDIS_PASSWORD:
    CELERY_BROKER_URL = 'redis://user:%s@%s:%s/%s' % (REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, DB_NUM[0])
    CELERY_RESULT_BACKEND = 'redis://user:%s@%s:%s/%s' % (REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, DB_NUM[1])
    REDISKV = redis.StrictRedis(
        host=REDIS_HOST,
        password=REDIS_PASSWORD,
        port=6379,
        db=DB_NUM[2]
    )
else:
    CELERY_BROKER_URL = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, DB_NUM[0])
    CELERY_RESULT_BACKEND = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, DB_NUM[1])
    REDISKV = redis.StrictRedis(
        host=REDIS_HOST,
        port=6379,
        db=DB_NUM[2]
    )

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

CELERY_TASK_ACKS_LATE = True
CELERYD_PREFETCH_MULTIPLIER = 1
CELERYD_MAX_TASKS_PER_CHILD = 5



CELERY_BEAT_SCHEDULE = {
    'get_latest_block': {
        'task': 'main.tasks.get_latest_block',
        'schedule': 5
    },
    'manage_block_transactions': {
        'task': 'main.tasks.manage_block_transactions',
        'schedule': 7
    },
    'problematic_transactions': {
        'task': 'main.tasks.problematic_transactions',
        'schedule': 3
    }
}

CORS_ORIGIN_WHITELIST = [
    "https://tokensale-staging.scibizinformatics.com",
    "https://tokensale.scibizinformatics.com"
]

if DEBUG:
    CORS_ORIGIN_WHITELIST += ['http://localhost:8000']


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
}

ACCESS_TOKEN_LIFETIME = int(config("ACCESS_TOKEN_LIFETIME", "0"))
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=ACCESS_TOKEN_LIFETIME or 1)
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "JWT": {
            "description": 'Input as "Bearer <token_here>"',
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
        }
    },
}

#Telegram bot settings
# TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_BOT_TOKEN = "1764241013:AAGA5L8vuZf8CBJH3iHkFsp84pRbFzSGwrc"
TELEGRAM_BOT_USER = decipher(config('TELEGRAM_BOT_USER', default=''))
TELEGRAM_DESTINATION_ADDR = decipher(config('TELEGRAM_DESTINATION_ADDR', default=''))


# Slack credentials and configurations

SLACK_BOT_USER_TOKEN = config('SLACK_BOT_USER_TOKEN', default='')
SLACK_VERIFICATION_TOKEN = config('SLACK_VERIFICATION_TOKEN', default='')
SLACK_CLIENT_ID = config('SLACK_CLIENT_ID', default='')
SLACK_CLIENT_SECRET = config('SLACK_CLIENT_SECRET', default='')
SLACK_SIGNING_SECRET = config('SLACK_SIGNING_SECRET', default='')

SLACK_DESTINATION_ADDR = 'https://watchtower.scibizinformatics.com/slack/notify/'
SLACK_THEME_COLOR = '#82E0AA'


MAX_BLOCK_TRANSACTIONS = 500
MAX_BLOCK_AWAY = 4000
MAX_RESTB_RETRIES = 14
MAX_SLPBITCOIN_SOCKET_DURATION = 10
MAX_BITSOCKET_DURATION = 10
BITDB_QUERY_LIMIT_PER_PAGE = 1000
TRANSACTIONS_PER_CHUNK=100

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[%(asctime)s %(name)s] %(levelname)s [%(pathname)s:%(lineno)d] - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'main': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    },
}

REDIS_CHANNEL_DB = [0, 1][DEPLOYMENT_INSTANCE == 'prod']
REDIS_CHANNEL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_CHANNEL_DB}"

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_CHANNEL]
        }
    }
}


# websocket vars
WATCH_ROOM = 'watch_room'