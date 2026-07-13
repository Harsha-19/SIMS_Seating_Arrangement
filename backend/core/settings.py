import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool = False) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_list(name: str, default: list[str]) -> list[str]:
    raw_value = os.environ.get(name)
    if not raw_value:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _get_path(name: str, default: str) -> Path:
    raw_value = os.environ.get(name)
    if not raw_value:
        return BASE_DIR / default

    candidate = Path(raw_value)
    if candidate.is_absolute():
        return candidate

    return BASE_DIR / candidate


_load_env_file(ENV_FILE)

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-5)@b+78hd^08sbxhbw%v3@^606n5qsh!(m$$j0q3^pop5j!)%z",
)
DEBUG = _get_bool("DEBUG", True)
ALLOWED_HOSTS = _get_list("ALLOWED_HOSTS", ["127.0.0.1", "localhost"])
FRONTEND_ORIGINS = _get_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://127.0.0.1:5173", "http://localhost:5173"],
)
ENABLE_REQUEST_LOGGING = _get_bool("ENABLE_REQUEST_LOGGING", False)
ENABLE_BROWSABLE_API = _get_bool("ENABLE_BROWSABLE_API", DEBUG)
ENABLE_API_THROTTLING = _get_bool("ENABLE_API_THROTTLING", False)
API_CACHE_TIMEOUT = int(os.environ.get("API_CACHE_TIMEOUT", "60"))
CACHE_BACKEND = os.environ.get("CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache")
CACHE_LOCATION = os.environ.get("CACHE_LOCATION", "exam-seating-cache")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "api.middleware.RequestLoggingMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "api.middleware.IgnoreWellKnownMiddleware",
]

ROOT_URLCONF = "core.urls"

CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CSRF_TRUSTED_ORIGINS = _get_list("CSRF_TRUSTED_ORIGINS", FRONTEND_ORIGINS)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "api.renderers.StandardizedJSONRenderer",
    ],
}

if ENABLE_BROWSABLE_API:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append("rest_framework.renderers.BrowsableAPIRenderer")

if ENABLE_API_THROTTLING:
    REST_FRAMEWORK.update({
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "anon": os.environ.get("API_THROTTLE_ANON", "120/minute"),
            "user": os.environ.get("API_THROTTLE_USER", "240/minute"),
        },
    })

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [path for path in [BASE_DIR / "templates"] if path.exists()],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _get_path("SQLITE_PATH", "db.sqlite3"),
    }
}

CACHES = {
    "default": {
        "BACKEND": CACHE_BACKEND,
        "LOCATION": CACHE_LOCATION,
        "TIMEOUT": API_CACHE_TIMEOUT,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [path for path in [BASE_DIR / "static"] if path.exists()]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "api": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "api.requests": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "api.upload": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
