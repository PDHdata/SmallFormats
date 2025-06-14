"""
Django settings for smallformats project.

Generated by 'django-admin startproject' using Django 4.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
import os
import dj_database_url
import django_cache_url
from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", 'django-insecure-r1ch4rd-g4rf13ld,-p.h.d.')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = SECRET_KEY.startswith('django-insecure-')

SMALLFORMATS_NAME = os.getenv("SMALLFORMATS_NAME", "Nameless Knockoff")

# SECURITY WARNING: don't leak this
MOXFIELD_API_KEY = os.environ.get('SMALLFORMATS_MOXFIELD_USERAGENT')

ALLOWED_HOSTS = [
    '.localhost',
    '127.0.0.1',
    '[::1]',
    'pdhdata.fly.dev',
    'pdhdata.com',
    'www.pdhdata.com',
]

CSRF_TRUSTED_ORIGINS = [
    'http://*.localhost',
    'http://127.0.0.1',
    'http://[::1]',
    'https://pdhdata.fly.dev',
    'https://pdhdata.com',
    'https://www.pdhdata.com',
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.postgres',
    'debug_toolbar',
    'django_htmx',
    'decklist.apps.DecklistConfig',
    'crawler.apps.CrawlerConfig',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    idx = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(idx + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')

INTERNAL_IPS = [
    "127.0.0.1",
]

ROOT_URLCONF = 'smallformats.urls'

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
                'smallformats.context_processors.sitename',
                'smallformats.context_processors.links',
            ],
        },
    },
]

WSGI_APPLICATION = 'smallformats.wsgi.application'
ASGI_APPLICATION = 'smallformats.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    # reads DATABASE_URL from the environment
    'default': dj_database_url.config(
        default="postgres://localhost/pdhdev",
        # default="sqlite:///" + os.path.join(BASE_DIR, 'db.sqlite3'),
    ),
}

# Caching

CACHES = {
    # reads CACHE_URL from the environment
    'default': django_cache_url.config(
        default="locmem://",
    )
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = 'decklist.User'

LOGIN_URL = reverse_lazy('admin:login')


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = '/app/static'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
