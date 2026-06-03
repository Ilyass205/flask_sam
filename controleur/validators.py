# coding: utf-8
"""
controleur/validators.py
========================
Validation des données d'entrée (réutilisable).

Responsabilité:
    - Valider IP, noms, protocoles, etc.
    - Regex et checks
    - Utilisé par tous les contrôleurs

Pourquoi:
    - Éviter dépendance CircleImport
    - Réutilisable (ne dépend que de regex/stdlib)
    - Facile à tester
"""

import re
from ipaddress import ip_address
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Erreur de validation destinée aux réponses HTTP 400."""


def get_json_payload(req, allowed_fields, required_fields=()):
    """
    Charge un body JSON objet et rejette les champs inattendus.
    """
    data = req.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Corps JSON invalide")

    allowed = set(allowed_fields)
    unexpected = sorted(set(data) - allowed)
    if unexpected:
        raise ValidationError("Champs non autorisés: " + ", ".join(unexpected))

    missing = [field for field in required_fields if data.get(field) in (None, '')]
    if missing:
        raise ValidationError("Champs requis: " + ", ".join(missing))

    return data


def normalise_string(value, field, min_len=1, max_len=100, allow_none=False):
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} doit être une chaîne")
    value = value.strip()
    if len(value) < min_len or len(value) > max_len:
        raise ValidationError(f"{field} doit contenir entre {min_len} et {max_len} caractères")
    return value


def normalise_int(value, field, min_value=1, max_value=None, allow_none=False):
    if value in (None, '') and allow_none:
        return None
    if isinstance(value, bool):
        raise ValidationError(f"{field} doit être un entier")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} doit être un entier")
    if parsed < min_value:
        raise ValidationError(f"{field} doit être supérieur ou égal à {min_value}")
    if max_value is not None and parsed > max_value:
        raise ValidationError(f"{field} doit être inférieur ou égal à {max_value}")
    return parsed


def require_choice(value, field, choices):
    if value not in choices:
        raise ValidationError(f"{field} invalide")
    return value


def validation_message(message):
    return {"success": False, "message": message}


def valide_login(login):
    if not login or not isinstance(login, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9_.@-]{3,50}$', login.strip()))


def valide_mot_de_passe(mdp):
    return isinstance(mdp, str) and 8 <= len(mdp) <= 128


def valide_ip(ip):
    """
    Valide une adresse IP ou URL RTSP/HTTP.
    
    Formats acceptés:
        - IP brute: 192.168.1.100
        - URL RTSP: rtsp://admin:pass@192.168.1.100:554/stream
        - URL HTTP: http://192.168.1.100:8080/video
    
    Args:
        ip (str): Adresse à valider
    
    Retour:
        bool: True si valide, False sinon
    
    Exemples:
        valide_ip("192.168.1.1")                    → True
        valide_ip("rtsp://admin:pass@192.168.1.1") → True
        valide_ip("256.256.256.256")                → False
        valide_ip("")                               → False
    """
    if not ip or not isinstance(ip, str):
        return False
    
    ip = ip.strip()
    
    # URL complète (RTSP ou HTTP)
    if ip.startswith('rtsp://') or ip.startswith('http://') or ip.startswith('https://'):
        parsed = urlparse(ip)
        if parsed.scheme not in ('rtsp', 'http', 'https') or not parsed.hostname:
            return False
        if parsed.port is not None and not valide_port(parsed.port):
            return False
        return _valide_host(parsed.hostname)

    return _valide_host(ip)


def _valide_host(host):
    if not host or not isinstance(host, str):
        return False
    host = host.strip()

    try:
        ip_address(host)
        return True
    except ValueError:
        pass

    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', host):
        return False
    
    if len(host) > 253:
        return False
    if host.lower() == 'localhost':
        return True
    hostname = r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$'
    return bool(re.match(hostname, host))


def valide_nom(nom, min_len=3, max_len=50):
    """
    Valide un nom (caméra, machine, etc).
    
    Règles:
        - Non vide
        - Entre min_len et max_len caractères
        - Alphanumérique + espaces + tirets + underscores
        - Pas de caractères spéciaux dangereux
    
    Args:
        nom (str): Nom à valider
        min_len (int): Longueur minimale (défaut: 3)
        max_len (int): Longueur maximale (défaut: 50)
    
    Retour:
        bool: True si valide, False sinon
    
    Exemples:
        valide_nom("Caméra 01")           → True
        valide_nom("Fraiseuse-CNC_1")     → True
        valide_nom("AB")                  → False (< 3 caractères)
        valide_nom("a"*51)                → False (> 50 caractères)
        valide_nom("Caméra<script>")      → False (caractère dangereux)
    """
    if not nom or not isinstance(nom, str):
        return False
    
    nom = nom.strip()
    
    # Vérifier longueur
    if len(nom) < min_len or len(nom) > max_len:
        return False
    
    # Regex: lettres (a-z, A-Z), chiffres, espaces, tirets, underscores
    # Exclure: <, >, ", ', ;, /, \, etc.
    pattern = r'^[a-zA-Z0-9\s\-_éèêëÉÈÊËÀÂÄÙÛÜÔÖÇ]+$'
    return bool(re.match(pattern, nom))


def valide_protocole(protocole):
    """
    Valide le protocole de caméra.
    
    Protocoles acceptés: RTSP, ONVIF, HTTP
    
    Args:
        protocole (str): Protocole à valider
    
    Retour:
        bool: True si dans la liste acceptée
    
    Exemples:
        valide_protocole("RTSP")   → True
        valide_protocole("ONVIF")  → True
        valide_protocole("rtsp")   → False (case-sensitive)
        valide_protocole("MQTT")   → False (non supporté)
    """
    return protocole in ['RTSP', 'ONVIF', 'HTTP']


def valide_id(id_val):
    """
    Valide un ID (numérique, > 0).
    
    Args:
        id_val: ID à valider (int ou str)
    
    Retour:
        bool: True si ID valide
    
    Exemples:
        valide_id(1)     → True
        valide_id("1")   → True
        valide_id(0)     → False
        valide_id(-1)    → False
        valide_id("abc") → False
    """
    try:
        id_int = int(id_val)
        return id_int > 0
    except (ValueError, TypeError):
        return False


def valide_email(email):
    """
    Valide une adresse email (basique).
    
    Args:
        email (str): Email à valider
    
    Retour:
        bool: True si format valide
    
    Exemples:
        valide_email("admin@example.com")  → True
        valide_email("invalid@")           → False
        valide_email("")                   → False
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def valide_date(date_str, format='%Y-%m-%d'):
    """
    Valide une date au format spécifié.
    
    Args:
        date_str (str): Date en string
        format (str): Format attendu (défaut: YYYY-MM-DD)
    
    Retour:
        bool: True si format valide
    
    Exemples:
        valide_date("2024-03-15")  → True
        valide_date("15-03-2024")  → False
        valide_date("")            → False
    """
    from datetime import datetime
    try:
        datetime.strptime(date_str, format)
        return True
    except (ValueError, TypeError):
        return False


def valide_port(port):
    """
    Valide un port réseau (1-65535).
    
    Args:
        port: Port à valider (int ou str)
    
    Retour:
        bool: True si port valide
    
    Exemples:
        valide_port(3306)    → True
        valide_port("5000")  → True
        valide_port(0)       → False
        valide_port(99999)   → False
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False
