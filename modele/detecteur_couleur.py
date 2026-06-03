# coding: utf-8
"""
detecteur_couleur.py
====================
Architecture Producer / Consumer — comme les vraies plateformes industrielles.

Principe :
    - Chaque thread caméra (producer) capte les frames et les pousse dans une queue
    - Un seul worker YOLO (consumer) dépile les frames et fait l'inférence
    - Résultat : zéro crash PyTorch, scalable à N caméras

Flux :
    Thread Cam 8 ──┐
    Thread Cam 9 ──┼──> Queue frames ──> Worker YOLO unique ──> API Flask / BDD
    Thread Cam N ──┘
"""

import cv2
import numpy as np
import threading
import queue
import time
import requests
import os
from logger import get_logger

log = get_logger('DETECT')

# ── Paramètres ────────────────────────────────────────────────
STABLE_FRAMES  = 4       # frames consécutives identiques pour valider une couleur
COOLDOWN_SECS  = 5       # délai min entre deux envois pour la même machine
CONFIDENCE_MIN = 0.55    # seuil de confiance YOLO
MAX_BACKOFF    = 30.0    # délai max en cas d'erreur réseau
BACKOFF_FACTOR = 2.0
ARUCO_MAX_DIST = 850     # distance max pixels colonne ↔ ArUco
ARUCO_DICT     = cv2.aruco.DICT_4X4_50

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'colonne_lumineuse.pt')

# Correspondance couleur → id_couleur BDD
COULEUR_TO_ID = {'red': 1, 'orange': 2, 'green': 3, 'off': 4}

# ── Queue globale frames ──────────────────────────────────────
# Les threads caméra poussent ici, le worker YOLO dépile.
# maxsize=30 : si le worker est trop lent on drop les vieilles frames
_frame_queue = queue.Queue(maxsize=30)

# ── Modèle YOLO — chargé une seule fois par le worker ─────────
_modele      = None
_modele_lock = threading.Lock()


def get_modele():
    """
    Charge le modèle YOLO une seule fois.
    Appelé uniquement par le worker YOLO — jamais par les threads caméra.
    L'appel factice force la fusion PyTorch avant la vraie utilisation.
    """
    global _modele
    with _modele_lock:
        if _modele is None:
            try:
                import torch
                torch.set_num_threads(1)
                from ultralytics import YOLO

                _modele = YOLO(MODEL_PATH)
                _modele.to('cpu')

                # Appel factice pour déclencher la fusion PyTorch immédiatement
                # (évite le crash 'bn' au premier vrai appel)
                dummy = np.zeros((64, 64, 3), dtype=np.uint8)
                _modele(dummy, verbose=False)

                log.info(f"Modèle YOLO chargé et prêt sur CPU : {MODEL_PATH}")
            except Exception as e:
                log.error(f"Impossible de charger YOLO : {e}")
    return _modele


# ── Détection couleur par luminosité ──────────────────────────

def detecter_couleur_colonne(frame, x1, y1, x2, y2):
    """
    Détecte quelle zone est allumée en comparant la luminosité des 3 tiers.
    Rouge = haut, Orange = milieu, Vert = bas.
    Robuste à la surexposition caméra car on compte les pixels très lumineux.
    """
    h = y2 - y1
    if h < 30:
        return None

    # Coupe le socle blanc en bas (faussait les détections)
    y2 = y2 - int(h * 0.30)
    h  = y2 - y1
    if h < 20:
        return None

    # Réduit les bords pour ne garder que le cœur lumineux
    margin_x = int((x2 - x1) * 0.20)
    x1 += margin_x
    x2 -= margin_x

    tiers = h // 3
    zones = {
        'red':    frame[y1:y1 + tiers,             x1:x2],
        'orange': frame[y1 + tiers:y1 + 2 * tiers, x1:x2],
        'green':  frame[y1 + 2 * tiers:y2,         x1:x2],
    }

    luminosites = {}
    for nom, roi in zones.items():
        if roi.size == 0:
            luminosites[nom] = 0
            continue
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        luminosites[nom] = cv2.countNonZero(thresh)

    log.debug(
        f"Luminosités → rouge:{luminosites['red']} "
        f"orange:{luminosites['orange']} vert:{luminosites['green']}"
    )

    best     = max(luminosites, key=luminosites.get)
    best_val = luminosites[best]
    autres   = [v for k, v in luminosites.items() if k != best]

    if best_val < 100:
        return 'off'
    if best_val < max(autres) * 1.5:
        return None

    return best


# ── Détection ArUco ───────────────────────────────────────────

def _detecter_aruco(frame, draw=False, max_id=50):
    """
    Détecte les marqueurs ArUco dans la frame.
    max_id filtre les faux positifs (ex: horloge caméra confondue avec marqueur).
    """
    aruco_dict   = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    aruco_params = cv2.aruco.DetectorParameters()

    # Permet de détecter les petits marqueurs (cam éloignée)
    aruco_params.minMarkerPerimeterRate    = 0.02
    aruco_params.adaptiveThreshWinSizeMin  = 3
    aruco_params.adaptiveThreshWinSizeMax  = 23

    detector        = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    corners, ids, _ = detector.detectMarkers(frame)
    result          = []

    if ids is not None:
        for i, corner in enumerate(corners):
            aruco_id = int(ids[i][0])
            if aruco_id > max_id:
                log.debug(f"ArUco#{aruco_id} ignoré (faux positif)")
                continue
            pts = corner[0].astype(int)
            cx  = int(pts[:, 0].mean())
            cy  = int(pts[:, 1].mean())
            result.append((aruco_id, cx, cy))
            if draw:
                cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
                cv2.putText(frame, f"ArUco#{aruco_id}", (cx + 8, cy - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    return result


def _associer_machine(cx, cy, aruco_list, machines_aruco):
    """
    Associe une colonne détectée à une machine via l'ArUco le plus proche.
    Retourne id_machine ou None si aucun ArUco assez proche.
    """
    best_id, best_dist = None, ARUCO_MAX_DIST
    for (aruco_id, ax, ay) in aruco_list:
        dist = ((cx - ax)**2 + (cy - ay)**2)**0.5
        if dist < best_dist and aruco_id in machines_aruco:
            best_dist = dist
            best_id   = machines_aruco[aruco_id]
    return best_id


# ── Worker YOLO unique ────────────────────────────────────────
# C'est LE cœur de l'architecture pro.
# Un seul thread fait l'inférence YOLO pour TOUTES les caméras.
# Les threads caméra lui envoient leurs frames via _frame_queue.

class _YoloWorker(threading.Thread):
    """
    Worker YOLO unique — consumer de la queue globale.
    
    Reçoit des tuples (detector_thread, frame) depuis la queue,
    fait l'inférence YOLO, puis appelle detector._process_results().
    
    Avantages :
        - Un seul accès PyTorch → zéro crash
        - Scalable : N caméras, toujours un seul worker
        - Architecture standard de l'industrie vidéo/IA
    """

    def __init__(self):
        super().__init__(daemon=True, name="yolo-worker")

    def run(self):
        log.info("Worker YOLO démarré — en attente de frames...")
        model = get_modele()

        while True:
            try:
                # Attend une frame — timeout 1s pour ne pas bloquer indéfiniment
                item = _frame_queue.get(timeout=1)
            except queue.Empty:
                continue

            if item is None:
                continue

            detector, frame = item

            try:
                # L'inférence YOLO se fait ICI, dans un seul thread → stable
                results = model(frame, verbose=False, conf=CONFIDENCE_MIN)
                detector._process_results(frame, results)
            except Exception as e:
                log.error(f"Worker YOLO erreur : {e}")


# Instance globale du worker — démarrée une seule fois au chargement du module
_yolo_worker = _YoloWorker()
_yolo_worker.start()


# ── Thread de détection par caméra (producer) ─────────────────
# Ne fait PLUS d'inférence YOLO directement.
# Se contente de capturer les frames et de les pousser dans la queue.

class _DetectionThread(threading.Thread):

    def __init__(self, cam_mgr, camera_id, machines_aruco, api_base_url):
        super().__init__(daemon=True, name=f"detect-{camera_id}")
        self.cam_mgr        = cam_mgr
        self.camera_id      = camera_id
        self.machines_aruco = machines_aruco   # {aruco_id: id_machine}
        self.api_base_url   = api_base_url.rstrip('/')
        self._running       = True


        # État interne de stabilisation par machine
        self._last_color  = {}
        self._last_time   = {}
        self._candidate   = {}
        self._stable      = {}
        self._error_count = 0
        self._lock        = threading.Lock()  # protège l'état interne

    def stop(self):
        self._running = False

    def _get_frame(self):
        """Récupère la dernière frame depuis le CameraManager."""
        with self.cam_mgr._lock:
            t = self.cam_mgr._threads.get(self.camera_id)
        return t.last_frame if t else None

    def run(self):
        """
        Boucle principale du thread caméra.
        Rôle : capturer les frames et les pousser dans la queue pour le worker YOLO.
        Ne fait PAS d'inférence ici — c'est le worker qui s'en charge.
        """
        log.info(f"Détecteur démarré cam={self.camera_id} machines={self.machines_aruco}")


        while self._running:
            frame_bytes = self._get_frame()
            if not frame_bytes:
                time.sleep(0.5)
                continue

            buf   = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is None:
                time.sleep(0.2)
                continue

            # Pousse la frame dans la queue si elle n'est pas pleine
            # Si pleine → on drop cette frame (le worker est occupé, on réessaiera)
            try:
                _frame_queue.put_nowait((self, frame))
            except queue.Full:
                pass  # queue pleine → on drop silencieusement cette frame

            time.sleep(0.1)  # ~10 fps d'analyse

        log.info(f"Détecteur arrêté cam={self.camera_id}")

    def _process_results(self, frame, results):
        aruco_list = _detecter_aruco(frame, draw=False)

        boxes_cl0 = [
            b for b in (results[0].boxes if results else [])
            if int(b.cls[0]) == 0
        ]
        if not boxes_cl0:
            return

        # Trie : d'abord les bbox avec ArUco proche, ensuite par aire
        def _score_box(b):
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            a_aruco = _associer_machine(cx, cy, aruco_list, self.machines_aruco) is not None
            aire    = (x2 - x1) * (y2 - y1)
            return (a_aruco, aire)

        boxes_cl0 = sorted(boxes_cl0, key=_score_box, reverse=True)

        machines_traitees = set()

        for box in boxes_cl0:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            if (x2-x1) * (y2-y1) < 5000:
                continue

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2


            id_machine = _associer_machine(cx, cy, aruco_list, self.machines_aruco)

            if id_machine is None:
                continue


            if id_machine in machines_traitees:
                continue
            machines_traitees.add(id_machine)

            couleur = detecter_couleur_colonne(frame, x1, y1, x2, y2)
            if couleur is None:
                continue

            with self._lock:
                if couleur == self._candidate.get(id_machine):
                    self._stable[id_machine] = self._stable.get(id_machine, 0) + 1
                else:
                    self._candidate[id_machine] = couleur
                    self._stable[id_machine]    = 1

                now = time.time()
                if (
                    self._stable.get(id_machine, 0) >= STABLE_FRAMES
                    and couleur != self._last_color.get(id_machine)
                    and (now - self._last_time.get(id_machine, 0)) >= COOLDOWN_SECS
                ):
                    id_couleur = COULEUR_TO_ID[couleur]
                    if self._envoyer(id_machine, id_couleur, couleur):
                        self._last_color[id_machine] = couleur
                        self._last_time[id_machine]  = now
                        self._error_count            = 0
                    else:
                        self._error_count += 1

    def _envoyer(self, id_machine, id_couleur, couleur):
        """Envoie l'événement à l'API Flask pour mise à jour BDD + dashboard."""
        try:
            r = requests.post(
                f"{self.api_base_url}/api/evenements",
                json={"id_machine": id_machine, "id_couleur": id_couleur},
                timeout=3
            )
            if r.status_code == 200:
                log.info(f"Cam {self.camera_id} → machine {id_machine} = {couleur.upper()} (id={id_couleur})")
                return True
            log.warning(f"Cam {self.camera_id} → HTTP {r.status_code}")
            return False
        except Exception as e:
            log.error(f"Cam {self.camera_id} → envoi échoué : {e}")
            return False


# ── Gestionnaire principal ────────────────────────────────────

class DetecteurCouleur:
    """
    Gestionnaire des threads de détection — un par caméra active.
    Le worker YOLO unique est démarré au chargement du module,
    indépendamment du nombre de caméras.
    """

    def __init__(self, cam_mgr, api_base_url="http://127.0.0.1:5000"):
        self._cam_mgr      = cam_mgr
        self._api_base_url = api_base_url
        self._threads      = {}
        self._lock         = threading.Lock()

    def start(self, id_camera, machines_aruco):
        """Lance la détection pour une caméra. Ne fait rien si déjà actif."""
        with self._lock:
            t = self._threads.get(id_camera)
            if t and t.is_alive():
                return
            t = _DetectionThread(self._cam_mgr, id_camera, machines_aruco, self._api_base_url)
            t.start()
            self._threads[id_camera] = t

    def stop(self, id_camera):
        """Arrête le thread de détection d'une caméra."""
        with self._lock:
            t = self._threads.pop(id_camera, None)
            if t:
                t.stop()

    def stop_all(self):
        """Arrête tous les threads — appelé à l'extinction du serveur."""
        for cid in list(self._threads.keys()):
            self.stop(cid)