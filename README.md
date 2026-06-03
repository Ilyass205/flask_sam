# JOGAM SAMv2 — Serveur de Supervision

Flask server for real-time supervision of industrial machines via IP cameras. Detects the state of luminous columns (signal towers) using YOLO and ArUco markers, logs machine events, and exposes a full REST API with a web dashboard.

---

## Features

- **Real-time camera streaming** — MJPEG streams from multiple RTSP/IP cameras
- **YOLO + ArUco detection** — detects signal tower colors (red / orange / green / off) and maps them to machines via ArUco markers
- **Machine supervision** — tracks state changes, logs events, triggers alerts
- **Dashboard** — live overview of all machines and their current states
- **Alert system** — configurable alerts per machine
- **Reports** — export events, states, and alerts as CSV or PDF
- **Statistics** — charts per machine, per event type, over time
- **Camera control** — PTZ, IR, LED, snapshot via API
- **User management** — role-based access (technicien / superviseur)

---

## Architecture

```
main.py
└── Application
    ├── Flask app + MySQL (flask-mysqldb)
    ├── CameraManager        — RTSP thread pool, one thread per camera
    ├── DetecteurCouleur     — producer/consumer YOLO pipeline
    │   ├── _DetectionThread (per camera) — captures frames → queue
    │   └── _YoloWorker (singleton)       — YOLO inference + ArUco
    ├── controleur/          — Flask route handlers (MVC controllers)
    └── modele/              — Database models and business logic
```

The YOLO worker is a single thread that processes frames from all cameras sequentially, avoiding PyTorch multi-threading crashes. Camera threads act as producers; the worker is the sole consumer.

---

## Stack

| Layer | Technology |
|---|---|
| Web framework | Flask |
| Database | MySQL (flask-mysqldb) |
| Computer vision | OpenCV, Ultralytics YOLO, ArUco |
| Streaming | MJPEG over HTTP |
| Frontend | Jinja2 templates, vanilla JS |

---

## Getting Started

### Prerequisites

- Python 3.10+
- MySQL server with a `samv2` database
- IP cameras accessible via RTSP

### Installation

```bash
git clone https://github.com/Ilyass205/flask_sam.git
cd flask_sam
pip install flask flask-mysqldb python-dotenv opencv-python ultralytics requests
```

### Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
DB_HOST=localhost
DB_USER=technicien
DB_PASSWORD=yourpassword
DB_NAME=samv2
DB_PORT=3306

DEFAULT_RTSP_USER=admin
DEFAULT_RTSP_PASS=yourpassword

SECRET_KEY=change-this-secret-key
API_BASE_URL=http://127.0.0.1:5000
FLASK_DEBUG=False
```

### Database

Run the SQL update script to create the default users:

```bash
mysql samv2 < update_bdd.sql
```

Default credentials after setup:

| Login | Password | Role |
|---|---|---|
| technicien | tech2026 | technicien |
| superviseur | super2026 | superviseur |

### Run

```bash
python main.py
```

The server starts on `0.0.0.0:5000` and prints the local and network URLs.

---

## API Reference

### Cameras
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/cameras` | List cameras |
| POST | `/api/cameras` | Add camera |
| PUT | `/api/cameras/<id>` | Update camera |
| DELETE | `/api/cameras/<id>` | Delete camera |
| GET | `/video_feed/<id>` | MJPEG stream |
| GET | `/api/cameras/<id>/snap` | Snapshot |
| POST | `/api/cameras/<id>/ptz` | PTZ control |
| POST/GET | `/api/cameras/<id>/ir` | IR on/off |
| POST/GET | `/api/cameras/<id>/led` | LED on/off |

### Machines
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/machines` | List machines |
| POST | `/api/machines` | Add machine |
| PUT | `/api/machines/<id>` | Update machine |
| DELETE | `/api/machines/<id>` | Delete machine |
| GET | `/api/etat/<id>` | Current machine state |
| GET | `/api/historique/<id>` | Event history |

### Events & Alerts
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/evenements` | Insert event (used by detector) |
| GET | `/api/alertes` | List alerts |
| POST | `/api/alertes/ajouter` | Add alert |
| DELETE | `/api/alertes/<id>` | Delete alert |

### Stats
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats/dashboard` | Dashboard summary |
| GET | `/api/stats/etats` | State breakdown |
| GET | `/api/stats/evenements` | Event timeline |
| GET | `/api/stats/machines` | Per-machine stats |

### Reports
| Method | Endpoint | Description |
|---|---|---|
| GET | `/rapports/csv/complet` | Full CSV export |
| GET | `/rapports/csv/evenements` | Events CSV |
| GET | `/rapports/csv/etats` | States CSV |
| GET | `/rapports/csv/alertes` | Alerts CSV |
| GET | `/rapports/pdf` | PDF report |

---

## Project Structure

```
flask_sam/
├── main.py                  # Entry point
├── application.py           # App factory + routing
├── config.py                # Config from .env
├── logger.py                # Logging setup
├── update_bdd.sql           # DB seed (default users)
├── controleur/              # Route handlers
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
├── modele/                  # DB models + detection
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
│   ├── detecteur_couleur.py # YOLO + ArUco pipeline
│   └── colonne_lumineuse.pt # YOLO model (trained)
├── templates/               # Jinja2 HTML templates
└── static/                  # CSS
```
