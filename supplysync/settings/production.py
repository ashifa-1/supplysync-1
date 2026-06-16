import os
from .base import *

DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'options': '-c search_path=supplysync,public',
        }
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get('REDIS_URL'),
    }
}

# Override JWT signing key if provided
if os.environ.get('JWT_SIGNING_KEY'):
    SIMPLE_JWT['SIGNING_KEY'] = os.environ.get('JWT_SIGNING_KEY')
elif SECRET_KEY:
    SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY
