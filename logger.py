# coding: utf-8
"""
logger.py — Gestion centralisée des logs SAMv2

Principe :
- Le fichier logs/session.log est recréé à chaque lancement (pas de rotation)
  → une session = un fichier propre, facile à consulter
- Le terminal n'affiche que les infos utiles (INFO et au-dessus)
  → plus de spam DEBUG dans la console
- Les DEBUG (luminosités, scores) vont uniquement dans le fichier de log
  → utiles pour déboguer mais pas besoin de les voir en permanence
"""

import logging
import os
from datetime import datetime

# Crée le dossier logs s'il n'existe pas
os.makedirs('logs', exist_ok=True)

# Format lisible : 2026-05-12 11:41:27 [CAM] INFO : message
_fmt_fichier  = logging.Formatter(
    '%(asctime)s [%(name)s] %(levelname)s : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
_fmt_terminal = logging.Formatter(
    '%(asctime)s [%(name)s] %(levelname)s : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Fichier de log de la session courante — recréé à chaque lancement
_SESSION_LOG = 'logs/session.log'

# Handler fichier global (créé une fois, partagé par tous les loggers)
_file_handler = None

def _get_file_handler():
    global _file_handler
    if _file_handler is None:
        # 'w' = recrée le fichier à chaque démarrage de l'appli
        _file_handler = logging.FileHandler(_SESSION_LOG, mode='w', encoding='utf-8')
        _file_handler.setLevel(logging.DEBUG)   # tout dans le fichier
        _file_handler.setFormatter(_fmt_fichier)

        # Entête dans le fichier pour savoir quand la session a démarré
        with open(_SESSION_LOG, 'w', encoding='utf-8') as f:
            f.write(f"{'='*60}\n")
            f.write(f"  SAMv2 — Session démarrée le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")

    return _file_handler


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour le module donné.
    
    - Fichier logs/session.log : reçoit TOUT (DEBUG, INFO, WARNING, ERROR)
    - Terminal : reçoit seulement INFO et au-dessus (plus de spam DEBUG)
    """
    log = logging.getLogger(name)
    if log.handlers:
        return log

    log.setLevel(logging.DEBUG)  # le logger lui-même accepte tout

    # Handler fichier — tout dedans, y compris les DEBUG (luminosités, scores...)
    log.addHandler(_get_file_handler())

    # Handler terminal — INFO seulement, pas de bruit
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(_fmt_terminal)
    log.addHandler(ch)

    return log


# Silence les libs trop bavardes
logging.getLogger('libav').setLevel(logging.ERROR)
logging.getLogger('ultralytics').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('CAM_CTRL').setLevel(logging.WARNING)
logging.getLogger('ultralytics').setLevel(logging.ERROR)