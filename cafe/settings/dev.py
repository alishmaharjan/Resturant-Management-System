from .base import *
from decouple import config

DEBUG = True

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,web',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='yasumi_db'),
        'USER': config('DB_USER', default='yasumi_user'),
        'PASSWORD': config('DB_PASSWORD', default='Yasumi@2024!'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
