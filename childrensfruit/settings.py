from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Sécurité ───────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='django-insecure-changeme-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,childrensfruit.org,www.childrensfruit.org', cast=Csv())

# Auto-include Railway domain if present
_RAILWAY_DOMAIN = config('RAILWAY_PUBLIC_DOMAIN', default='')
if _RAILWAY_DOMAIN and _RAILWAY_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_RAILWAY_DOMAIN)

# Auto-include Render domain if present
_RENDER_DOMAIN = config('RENDER_EXTERNAL_HOSTNAME', default='')
if _RENDER_DOMAIN and _RENDER_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_RENDER_DOMAIN)

# CSRF trusted origins (required for HTTPS forms in production)
CSRF_TRUSTED_ORIGINS = [
    'https://childrensfruit.org',
    'https://www.childrensfruit.org',
]
if _RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_RAILWAY_DOMAIN}')
if _RENDER_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_RENDER_DOMAIN}')

# ── Applications ──────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_apscheduler',
    'axes',
    'cloudinary_storage',
    'cloudinary',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',                # anti-brute-force
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'childrensfruit.urls'

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

WSGI_APPLICATION = 'childrensfruit.wsgi.application'

# ── Base de données ────────────────────────────────────────────
import dj_database_url as _dj_db

_DATABASE_URL = config('DATABASE_URL', default='')
if _DATABASE_URL:
    # Railway / PostgreSQL
    DATABASES = {'default': _dj_db.parse(_DATABASE_URL, conn_max_age=600)}
else:
    # Développement local SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Auth ───────────────────────────────────────────────────────
AUTH_USER_MODEL = 'core.CustomUser'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ── Axes (anti brute-force login) ──────────────────────────────
AXES_FAILURE_LIMIT     = 5          # blocage après 5 tentatives
AXES_COOLOFF_TIME      = 1          # débloqué après 1 heure
AXES_LOCKOUT_CALLABLE  = 'core.views.axes_lockout_response'
AXES_RESET_ON_SUCCESS  = True
AXES_ENABLE_ADMIN      = True

# ── Internationalisation ───────────────────────────────────────
LANGUAGE_CODE = 'fr'
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

# ── Cloudinary (stockage media permanent) ─────────────────────
_CLOUDINARY_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': _CLOUDINARY_NAME,
    'API_KEY':    config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# ── Fichiers statiques (WhiteNoise) ───────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG else
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
    'default': {
        # Cloudinary en production si configuré, FileSystem en local
        'BACKEND': (
            'cloudinary_storage.storage.MediaCloudinaryStorage'
            if _CLOUDINARY_NAME else
            'django.core.files.storage.FileSystemStorage'
        ),
    },
}

# ── Fichiers médias (uploads) ─────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Taille max upload global (100 Mo)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024     # 10 Mo pour les données POST
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024     # fichiers > 10 Mo → tmp file

# ── Email SMTP (LWS / tout hébergeur) ─────────────────────────
_EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')

if _EMAIL_HOST_USER:
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = config('EMAIL_HOST', default='mail.childrensfruit.org')
    EMAIL_PORT          = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS       = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_USE_SSL       = config('EMAIL_USE_SSL', default=False, cast=bool)
    EMAIL_HOST_USER     = _EMAIL_HOST_USER
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=f"Children's Fruit <{_EMAIL_HOST_USER or 'noreply@childrensfruit.org'}>"
)

# ── Sécurité HTTPS (production uniquement) ────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER      = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Railway healthcheck hits HTTPS public URL — redirect is safe
    SECURE_SSL_REDIRECT          = True
    SESSION_COOKIE_SECURE        = True
    CSRF_COOKIE_SECURE           = True
    SECURE_BROWSER_XSS_FILTER    = True
    SECURE_CONTENT_TYPE_NOSNIFF  = True
    SECURE_HSTS_SECONDS          = 31536000   # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD          = True
    X_FRAME_OPTIONS              = 'SAMEORIGIN'
    SESSION_COOKIE_HTTPONLY      = True
    CSRF_COOKIE_HTTPONLY         = True

# ── Google OAuth 2.0 ───────────────────────────────────────────
GOOGLE_CLIENT_ID     = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')
GOOGLE_REDIRECT_URI  = config('GOOGLE_REDIRECT_URI', default='http://127.0.0.1:8000/accounts/google/callback/')

# ── YouTube Data API v3 ────────────────────────────────────────
YOUTUBE_API_KEY  = config('YOUTUBE_API_KEY', default='')
YOUTUBE_CHANNEL  = config('YOUTUBE_CHANNEL', default='@CFRUIT24')

# ── APScheduler (sync YouTube toutes les heures) ───────────────
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25

# ── Misc ───────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
