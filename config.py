# coding: utf-8
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

DB_HOST     = os.environ.get('DB_HOST',     'localhost')
DB_USER     = os.environ.get('DB_USER',     'technicien')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME     = os.environ.get('DB_NAME',     'samv2')
DB_PORT     = int(os.environ.get('DB_PORT', 3306))

DEFAULT_RTSP_USER = os.environ.get('DEFAULT_RTSP_USER', 'admin')
DEFAULT_RTSP_PASS = os.environ.get('DEFAULT_RTSP_PASS', '')

SECRET_KEY                 = os.environ.get('SECRET_KEY', 'REMPLACER-CETTE-CLE')
PERMANENT_SESSION_LIFETIME = 3600
API_BASE_URL               = os.environ.get('API_BASE_URL', 'http://127.0.0.1:5000')
FLASK_DEBUG                = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

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
}