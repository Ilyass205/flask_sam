# coding: utf-8
"""
camera_manager.py — Streaming RTSP via ffmpeg (low-latency)
Fix : queue + watchdog pour éviter le blocage du read sur flux 4K HEVC
"""

import subprocess
import threading
import queue
import numpy as np
import cv2
import time
from logger import get_logger

log = get_logger('CAM')

JPEG_QUALITY   = 88
RETRY_DELAY    = 3.0
FRAME_INTERVAL = 0.04    # ~25fps
WATCHDOG_SECS  = 15.0

STREAM_WIDTH   = 854
STREAM_HEIGHT  = 480


class _CameraThread(threading.Thread):

    def __init__(self, source: str, camera_id: int):
        super().__init__(daemon=True, name=f"cam-{camera_id}")
        self.source      = source
        self.camera_id   = camera_id
        self._lock       = threading.Lock()
        self._last_frame = None
        self._running    = True

    @property
    def last_frame(self):
        with self._lock:
            return self._last_frame

    @last_frame.setter
    def last_frame(self, value):
        with self._lock:
            self._last_frame = value

    def stop(self):
        self._running = False

    def _build_ffmpeg_cmd(self):
        return [
            'ffmpeg',
            '-loglevel', 'quiet',
            '-rtsp_transport', 'tcp',
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
            '-analyzeduration', '1000000',
            '-probesize', '1000000',
            '-i', self.source.replace('h264Preview_01_main', 'h264Preview_01_sub'),
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-vf', f'scale={STREAM_WIDTH}:{STREAM_HEIGHT}',
            '-an',
            '-'
        ]

    def run(self):
        width, height = STREAM_WIDTH, STREAM_HEIGHT
        frame_size    = width * height * 3

        while self._running:
            log.info(f"Cam {self.camera_id} → connexion {self.source}")
            proc = None
            try:
                proc = subprocess.Popen(
                    self._build_ffmpeg_cmd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=10 * frame_size
                )
                log.info(f"Cam {self.camera_id} → connectée")

                q = queue.Queue(maxsize=2)

                def _reader(proc, q, fs):
                    try:
                        while True:
                            raw = proc.stdout.read(fs)
                            if len(raw) != fs:
                                break
                            if q.full():
                                try: q.get_nowait()
                                except queue.Empty: pass
                            q.put(raw)
                    except Exception:
                        pass
                    finally:
                        q.put(None)

                threading.Thread(
                    target=_reader,
                    args=(proc, q, frame_size),
                    daemon=True,
                    name=f"reader-{self.camera_id}"
                ).start()

                while self._running:
                    try:
                        raw = q.get(timeout=WATCHDOG_SECS)
                    except queue.Empty:
                        log.warning(f"Cam {self.camera_id} → watchdog {WATCHDOG_SECS}s, reconnexion")
                        break

                    if raw is None:
                        log.warning(f"Cam {self.camera_id} → flux perdu, reconnexion")
                        break

                    frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
                    ret, buf = cv2.imencode('.jpg', frame,
                                           [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                    if ret:
                        self.last_frame = buf.tobytes()

            except Exception as e:
                log.error(f"Cam {self.camera_id} → erreur : {e}")
            finally:
                if proc:
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                    except Exception:
                        pass

            if self._running:
                time.sleep(RETRY_DELAY)

        log.info(f"Cam {self.camera_id} → thread arrêté")


class CameraManager:

    def __init__(self):
        self._threads: dict[int, _CameraThread] = {}
        self._lock = threading.Lock()

    def start(self, camera_id: int, source: str):
        with self._lock:
            t = self._threads.get(camera_id)
            if t and not t.is_alive():
                self._threads.pop(camera_id)
                t = None
            if t:
                if t.source == source:
                    return
                t.stop()
                self._threads.pop(camera_id)
            t = _CameraThread(source, camera_id)
            t.start()
            self._threads[camera_id] = t
            log.info(f"Thread démarré pour caméra {camera_id}")

    def restart(self, camera_id: int, source: str):
        with self._lock:
            t = self._threads.pop(camera_id, None)
            if t: t.stop()
        time.sleep(0.5)
        self.start(camera_id, source)

    def stop(self, camera_id: int):
        with self._lock:
            t = self._threads.pop(camera_id, None)
            if t:
                t.stop()
                log.info(f"Thread arrêté pour caméra {camera_id}")

    def stop_all(self):
        for cid in list(self._threads.keys()):
            self.stop(cid)

    def get_frame(self, camera_id: int):
        with self._lock:
            t = self._threads.get(camera_id)
            if t and not t.is_alive():
                self._threads.pop(camera_id, None)
                t = None
        return t.last_frame if t else None

    def generate_frames(self, camera_id: int):
        while True:
            # CORRECTION : capture last_frame à l'intérieur du lock
            # pour éviter la race condition (t pouvait être stoppé entre
            # la sortie du with et l'accès à t.last_frame)
            frame_bytes = None
            running     = False
            with self._lock:
                t = self._threads.get(camera_id)
                if t and not t.is_alive():
                    self._threads.pop(camera_id, None)
                    t = None
                running = t is not None
                if t:
                    frame_bytes = t.last_frame  # lecture protégée par le lock

            if frame_bytes is None:
                frame_bytes = _no_signal_frame(
                    "Connexion en cours..." if running else "Caméra non démarrée"
                )
            yield (
                b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                + frame_bytes + b'\r\n'
            )
            time.sleep(FRAME_INTERVAL)


def _no_signal_frame(message: str = "Pas de signal") -> bytes:
    img   = np.full((STREAM_HEIGHT, STREAM_WIDTH, 3), 28, dtype=np.uint8)
    bruit = np.random.randint(0, 8, img.shape, dtype=np.uint8)
    img   = cv2.add(img, bruit)
    cx    = max(0, STREAM_WIDTH  // 2 - len(message) * 9)
    cy    = STREAM_HEIGHT // 2
    cv2.putText(img, message, (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (160, 160, 160), 2, cv2.LINE_AA)
    cv2.putText(img, time.strftime("%H:%M:%S"), (10, STREAM_HEIGHT - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (55, 55, 55), 1, cv2.LINE_AA)
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()