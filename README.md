# JOGAM SAMv2 — Serveur de Supervision

Serveur Flask de supervision en temps réel de machines industrielles via caméras IP. Détecte l'état des colonnes lumineuses (tours de signalisation) par YOLO et marqueurs ArUco, enregistre les événements machine et expose une API REST complète avec tableau de bord web.

---

## Fonctionnalités

- **Streaming caméra en temps réel** — flux MJPEG depuis plusieurs caméras RTSP/IP
- **Détection YOLO + ArUco** — détecte les couleurs des colonnes lumineuses (rouge / orange / vert / éteint) et les associe aux machines via marqueurs ArUco
- **Supervision machine** — suivi des changements d'état, journalisation des événements, déclenchement d'alertes
- **Tableau de bord** — vue d'ensemble en direct de toutes les machines et leur état courant
- **Système d'alertes** — alertes configurables par machine
- **Rapports** — export des événements, états et alertes en CSV ou PDF
- **Statistiques** — graphiques par machine, par type d'événement, dans le temps
- **Contrôle caméra** — PTZ, IR, LED, snapshot via API
- **Gestion des utilisateurs** — accès par rôle (technicien / superviseur)

---

## Architecture

```
main.py
└── Application
    ├── Flask app + MySQL (flask-mysqldb)
    ├── CameraManager        — pool de threads RTSP, un thread par caméra
    ├── DetecteurCouleur     — pipeline YOLO producteur/consommateur
    │   ├── _DetectionThread (par caméra) — capture les frames → queue
    │   └── _YoloWorker (singleton)       — inférence YOLO + ArUco
    ├── controleur/          — gestionnaires de routes Flask (contrôleurs MVC)
    └── modele/              — modèles base de données et logique métier
```

Le worker YOLO est un thread unique qui traite les frames de toutes les caméras séquentiellement, évitant les crashs PyTorch multi-thread. Les threads caméra sont des producteurs ; le worker est le seul consommateur.

---

## Stack technique

| Couche | Technologie |
|---|---|
| Framework web | Flask |
| Base de données | MySQL (flask-mysqldb) |
| Vision par ordinateur | OpenCV, Ultralytics YOLO, ArUco |
| Streaming | MJPEG over HTTP |
| Frontend | Templates Jinja2, JS vanilla |

---

## Démarrage rapide

### Prérequis

- Python 3.10+
- Serveur MySQL avec une base de données `samv2`
- Caméras IP accessibles via RTSP

### Installation

```bash
git clone https://github.com/Ilyass205/flask_sam.git
cd flask_sam
pip install -r requirements.txt
```

### Configuration

Copiez `.env.example` vers `.env` et renseignez vos valeurs :

```env
DB_HOST=localhost
DB_USER=technicien
DB_PASSWORD=votremotdepasse
DB_NAME=samv2
DB_PORT=3306

DEFAULT_RTSP_USER=admin
DEFAULT_RTSP_PASS=votremotdepasse

SECRET_KEY=changer-cette-cle-secrete
API_BASE_URL=http://127.0.0.1:5000
FLASK_DEBUG=False

# Activer en production derriere HTTPS
SESSION_COOKIE_SECURE=False
TRUST_PROXY_HEADERS=False
ENABLE_HSTS=False
HSTS_MAX_AGE=31536000
```

### Base de données

Exécutez le script SQL pour créer les utilisateurs par défaut :

```bash
mysql samv2 < update_bdd.sql
```

Identifiants par défaut après initialisation :

| Login | Mot de passe | Rôle |
|---|---|---|
| technicien | tech2026 | technicien |
| superviseur | super2026 | superviseur |

### Lancement

```bash
python main.py
```

Le serveur démarre sur `0.0.0.0:5000` et affiche les URLs locale et réseau.

---

## Référence API

### Caméras
| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/cameras` | Lister les caméras |
| POST | `/api/cameras` | Ajouter une caméra |
| PUT | `/api/cameras/<id>` | Modifier une caméra |
| DELETE | `/api/cameras/<id>` | Supprimer une caméra |
| GET | `/video_feed/<id>` | Flux MJPEG |
| GET | `/api/cameras/<id>/snap` | Snapshot |
| POST | `/api/cameras/<id>/ptz` | Contrôle PTZ |
| POST/GET | `/api/cameras/<id>/ir` | IR on/off |
| POST/GET | `/api/cameras/<id>/led` | LED on/off |

### Machines
| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/machines` | Lister les machines |
| POST | `/api/machines` | Ajouter une machine |
| PUT | `/api/machines/<id>` | Modifier une machine |
| DELETE | `/api/machines/<id>` | Supprimer une machine |
| GET | `/api/etat/<id>` | État courant de la machine |
| GET | `/api/historique/<id>` | Historique des événements |

### Événements & Alertes
| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/evenements` | Insérer un événement (utilisé par le détecteur) |
| GET | `/api/alertes` | Lister les alertes |
| POST | `/api/alertes/ajouter` | Ajouter une alerte |
| DELETE | `/api/alertes/<id>` | Supprimer une alerte |

### Statistiques
| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/stats/dashboard` | Résumé tableau de bord |
| GET | `/api/stats/etats` | Répartition des états |
| GET | `/api/stats/evenements` | Chronologie des événements |
| GET | `/api/stats/machines` | Statistiques par machine |

### Rapports
| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/rapports/csv/complet` | Export CSV complet |
| GET | `/rapports/csv/evenements` | CSV événements |
| GET | `/rapports/csv/etats` | CSV états |
| GET | `/rapports/csv/alertes` | CSV alertes |
| GET | `/rapports/pdf` | Rapport PDF |

---

## Structure du projet

```
flask_sam/
├── main.py                  # Point d'entrée
├── application.py           # Fabrique d'application + routage
├── config.py                # Configuration depuis .env
├── logger.py                # Configuration des logs
├── update_bdd.sql           # Initialisation BDD (utilisateurs par défaut)
├── controleur/              # Gestionnaires de routes
│   ├── controleur_auth.py
│   ├── controleur_camera.py
│   ├── controleur_camera_ctrl.py
│   ├── controleur_machine.py
│   ├── controleur_association.py
│   ├── controleur_event.py
│   ├── controleur_stats.py
│   ├── controleur_report.py
│   ├── controleur_erreurs.py
│   └── validators.py
├── modele/                  # Modèles BDD + détection
│   ├── supervision_base.py
│   ├── supervision_camera.py
│   ├── supervision_machine.py
│   ├── supervision_auth.py
│   ├── supervision_association.py
│   ├── supervision_evenement.py
│   ├── supervision_alerte.py
│   ├── supervision_stats.py
│   ├── supervision_rapport.py
│   ├── camera_manager.py
│   ├── detecteur_couleur.py # Pipeline YOLO + ArUco
│   └── colonne_lumineuse.pt # Modèle YOLO (entraîné)
├── templates/               # Templates HTML Jinja2
└── static/                  # CSS
```
