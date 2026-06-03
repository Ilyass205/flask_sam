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
        return True
    
    # IP brute: valider avec regex
    # Pattern: \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, ip):
        parts = ip.split('.')
        try:
            # Vérifier que chaque octet est 0-255
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    return False


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
    pattern = r'^[a-zA-Z0-9\s\-_éèêëàâäùûüôöç]+$'
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
