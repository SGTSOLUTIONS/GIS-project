# settings.py
import os
from pathlib import Path
# settings.py - Add this at the very top
import os
import pymysql
pymysql.install_as_MySQLdb()
import sys

# GDAL Configuration for OSGeo4W
if os.name == 'nt':
    OSGEO4W_PATH = r'C:\OSGeo4W'
    
    # Add OSGeo4W bin to PATH
    os.environ['PATH'] = os.path.join(OSGEO4W_PATH, 'bin') + ';' + os.environ.get('PATH', '')
    
    # Set PROJ_LIB
    os.environ['PROJ_LIB'] = os.path.join(OSGEO4W_PATH, 'share', 'proj')
    
    # Set GDAL_DATA
    os.environ['GDAL_DATA'] = os.path.join(OSGEO4W_PATH, 'share', 'gdal')
    
    # CRITICAL: Set GDAL_LIBRARY_PATH to the exact DLL
    # Using GDAL 3.13.2 which you have
    GDAL_LIBRARY_PATH = os.path.join(OSGEO4W_PATH, 'bin', 'gdal313.dll')
    
    # Also add to sys.path for Python imports
    python_path = os.path.join(OSGEO4W_PATH, 'apps', 'Python312', 'Lib', 'site-packages')
    if os.path.exists(python_path) and python_path not in sys.path:
        sys.path.insert(0, python_path)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'z32l=fo1+zp#v==(k^i5p+&om1i0b6m0(#1hmy%stini5oy$&1'
DEBUG = True
ALLOWED_HOSTS = [
    # "https://api.sgtsolutions.in/",
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # Add this if using GIS
    'rest_framework',      # Add this
    'corsheaders',         # Add this
    'Nit',                 # Your app
    # ... other apps
]

# Add middleware (add at the top of MIDDLEWARE list)
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Add this at the top
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add CORS settings (at the bottom of settings.py)
CORS_ALLOW_ALL_ORIGINS = True  # For development only
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

ROOT_URLCONF = 'application.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'Nit', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'Nit.context_processors.sidebar_counts',
                'Nit.context_processors.data_list',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',  # ✅ GIS engine
        'NAME': 'gis_survey_db',
        'USER': 'root',
        'PASSWORD': 'root1234',  # ← YOU NEED A PASSWORD HERE
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'  # Changed from 'static/' to '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'Nit', 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Added for production

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Messages
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}