# coding: utf-8
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

def _bool_env(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


DB_HOST     = os.environ.get('DB_HOST',     'localhost')
DB_USER     = os.environ.get('DB_USER',     'technicien')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME     = os.environ.get('DB_NAME',     'samv2')
DB_PORT     = _int_env('DB_PORT', 3306)

DEFAULT_RTSP_USER = os.environ.get('DEFAULT_RTSP_USER', 'admin')
DEFAULT_RTSP_PASS = os.environ.get('DEFAULT_RTSP_PASS', '')

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY doit être défini dans l'environnement")

PERMANENT_SESSION_LIFETIME = 3600
API_BASE_URL               = os.environ.get('API_BASE_URL', 'http://127.0.0.1:5000')
FLASK_DEBUG                = _bool_env('FLASK_DEBUG', False)
SESSION_COOKIE_SECURE      = _bool_env('SESSION_COOKIE_SECURE', False)
TRUST_PROXY_HEADERS        = _bool_env('TRUST_PROXY_HEADERS', False)
ENABLE_HSTS                = _bool_env('ENABLE_HSTS', False)
HSTS_MAX_AGE               = _int_env('HSTS_MAX_AGE', 31536000)

FLASK_CONFIG = {
    'MYSQL_HOST':     DB_HOST,
    'MYSQL_USER':     DB_USER,
    'MYSQL_PASSWORD': DB_PASSWORD,
    'MYSQL_DB':       DB_NAME,
    'MYSQL_PORT':     DB_PORT,
    'SECRET_KEY':     SECRET_KEY,
    'PERMANENT_SESSION_LIFETIME': timedelta(seconds=PERMANENT_SESSION_LIFETIME),
    'API_BASE_URL':   API_BASE_URL,
    'DEFAULT_RTSP_USER': DEFAULT_RTSP_USER,
    'DEFAULT_RTSP_PASS': DEFAULT_RTSP_PASS,
    'DEBUG': FLASK_DEBUG,
    'SESSION_COOKIE_SECURE': SESSION_COOKIE_SECURE,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'TRUST_PROXY_HEADERS': TRUST_PROXY_HEADERS,
    'ENABLE_HSTS': ENABLE_HSTS,
    'HSTS_MAX_AGE': HSTS_MAX_AGE,
}
