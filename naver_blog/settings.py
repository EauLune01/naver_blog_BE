"""
Django settings for naver_blog project.

Generated by 'django-admin startproject' using Django 5.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-yg+9bm8rro588im9hkx+&ks-cubwfcohh*mq=p+v_*b4+&%$4n'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'main',
    'drf_yasg',
    'corsheaders'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'naver_blog.urls'

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

WSGI_APPLICATION = 'naver_blog.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'naver_blog',
        'USER': 'root',
        'PASSWORD': '20200129',
        'HOST': 'localhost',
        'PORT': '3306',
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

LANGUAGE_CODE = 'ko-kr'  # 한국어를 사용

TIME_ZONE = 'Asia/Seoul'  # 한국 표준시

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST framework의 기본 인증 클래스 및 필터링 설정
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}
# SimpleJWT 설정
from datetime import timedelta
SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,  # 리프레시 토큰 회전
    'BLACKLIST_AFTER_ROTATION': True,  # 리프레시 토큰 회전 후 블랙리스트 처리
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),  # 액세스 토큰 유효 기간 설정 (하루)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # 리프레시 토큰 유효 기간 설정 (7일)
}


AUTH_USER_MODEL = 'main.CustomUser'


# MEDIA_ROOT: 파일이 실제로 저장되는 경로
MEDIA_ROOT = os.path.join(BASE_DIR, 'main/media')

# MEDIA_URL: 브라우저에서 파일에 접근할 때 사용할 경로
MEDIA_URL = '/media/'

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'BearerAuth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': "JWT Token을 입력하세요. 형식: 'Bearer <토큰>'"
        }
    },
    'SECURITY_REQUIREMENTS': [{
        'BearerAuth': []
    }],
}
# 특정 도메인에서만 접근 허용
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",  # Live Server (프론트엔드 실행 주소)
]

# 모든 도메인 허용 (개발용)
CORS_ALLOW_ALL_ORIGINS = True

# 모든 HTTP 메서드 허용 (GET, POST, PUT, DELETE 등)
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

# 특정 헤더 허용
CORS_ALLOW_HEADERS = ["*"]