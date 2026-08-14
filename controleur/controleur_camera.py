# coding: utf-8
from flask import render_template, jsonify, request, Response
from modele.Supervision import Supervision
from controleur.validators import (
    ValidationError,
    get_json_payload,
    normalise_string,
    require_choice,
    validation_message,
    valide_ip,
    valide_nom,
    valide_protocole,
)


class ControleurCamera:

    def __init__(self, appli):
        self.mysql     = appli.mysql
        self.config    = appli.app.config
        self.cam_mgr   = appli.cam_mgr
        self.detecteur = appli.detecteur

    def _get_rtsp_url(self, camera):
        """Construit l'URL RTSP à partir de l'IP ou retourne l'URL si déjà complète."""
        if not camera or not camera.get('ip_camera'):
            return None
        source = camera['ip_camera']
        if source.startswith('rtsp://') or source.startswith('http'):
            return source
        user = self.config.get('DEFAULT_RTSP_USER', 'admin')
        pwd  = self.config.get('DEFAULT_RTSP_PASS', '')
        return f"rtsp://{user}:{pwd}@{source}:554/h264Preview_01_main"

    def _start_camera(self, id_camera):
        """Démarre le thread de streaming + le thread de détection pour une caméra."""
        model  = Supervision(self.mysql)
        camera = model.get_camera(id_camera)
        source = self._get_rtsp_url(camera)
        if not source:
            return
        self.cam_mgr.start(id_camera, source)
        machines_aruco = model.get_machines_aruco_par_camera(id_camera)
        if machines_aruco:
            self.detecteur.start(id_camera, machines_aruco)

    # ── Pages HTML ─────────────────────────────────────────────────────────────

    def afficher_index(self):
        model           = Supervision(self.mysql)
        machines        = model.get_machines()
        all_cameras     = model.get_all_cameras()
        associations    = model.get_cameras_avec_machines()
        alertes_recents = model.get_alertes(limite=5)
        return render_template("index.html",
            machines=machines, all_cameras=all_cameras,
            associations=associations, alertes_recents=alertes_recents)

    def afficher_camera(self, id_camera):
        """Page caméra — passe toutes les machines pour le sélecteur multi-machines."""
        model      = Supervision(self.mysql)
        camera     = model.get_camera(id_camera)
        machines   = model.get_machines_par_camera(id_camera)
        machine    = machines[0] if machines else None
        historique = model.get_historique_machine(machine['id_machine']) if machine else []
        self._start_camera(id_camera)
        return render_template("camera.html",
            camera=camera, machine=machine,
            machines=machines, historique=historique)

    def cameras_direct(self):
        model   = Supervision(self.mysql)
        cameras = model.get_all_cameras()
        for cam in cameras:
            self._start_camera(cam['id_camera'])
        return render_template("cameras_direct.html", cameras=cameras)

    # ── Streaming ──────────────────────────────────────────────────────────────

    def video_feed(self, id_camera):
        self._start_camera(id_camera)
        return Response(self.cam_mgr.generate_frames(id_camera),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    # ── API Caméras ────────────────────────────────────────────────────────────

    def api_get_cameras(self):
        model   = Supervision(self.mysql)
        cameras = model.get_cameras_avec_machines()
        return jsonify(self._serialise(cameras))

    def api_ajouter_camera(self):
        try:
            data  = get_json_payload(request, {'nom', 'ip', 'protocole'}, {'nom', 'ip'})
            nom   = normalise_string(data.get('nom'), 'nom', min_len=3, max_len=50)
            ip    = normalise_string(data.get('ip'), 'ip', min_len=3, max_len=255)
            proto = require_choice(data.get('protocole', 'RTSP'), 'protocole', ['RTSP', 'ONVIF', 'HTTP'])
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_nom(nom) or not valide_ip(ip) or not valide_protocole(proto):
            return jsonify({"success": False, "message": "Données caméra invalides"}), 400

        model = Supervision(self.mysql)
        ok    = model.ajouter_camera(nom, ip, proto)
        return jsonify({"success": ok})

    def api_modifier_camera(self, id_camera):
        try:
            data  = get_json_payload(request, {'nom', 'ip', 'protocole'}, {'nom', 'ip'})
            nom   = normalise_string(data.get('nom'), 'nom', min_len=3, max_len=50)
            ip    = normalise_string(data.get('ip'), 'ip', min_len=3, max_len=255)
            proto = require_choice(data.get('protocole', 'RTSP'), 'protocole', ['RTSP', 'ONVIF', 'HTTP'])
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_nom(nom) or not valide_ip(ip) or not valide_protocole(proto):
            return jsonify({"success": False, "message": "Données caméra invalides"}), 400

        self.cam_mgr.stop(id_camera)
        self.detecteur.stop(id_camera)
        model = Supervision(self.mysql)
        ok    = model.modifier_camera(id_camera, nom, ip, proto)
        return jsonify({"success": ok})

    def api_supprimer_camera(self, id_camera):
        self.cam_mgr.stop(id_camera)
        self.detecteur.stop(id_camera)
        model = Supervision(self.mysql)
        ok    = model.supprimer_camera(id_camera)
        return jsonify({"success": ok})

    @staticmethod
    def _serialise(rows):
        result = []
        for row in rows:
            r = dict(row)
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
            result.append(r)
        return result

    def test_yolo(self):
        model   = Supervision(self.mysql)
        cameras = model.get_all_cameras()
        for cam in cameras:
            self._start_camera(cam['id_camera'])
        return render_template("test_yolo.html", cameras=cameras)

    def test_yolo_feed(self, id_camera):
        """
        Flux vidéo annoté pour déboguer la détection YOLO + ArUco.

        Fix ArUco unique : chaque ArUco ne peut être lié qu'à UNE seule colonne
        (la plus proche). Si 2 colonnes sont proches du même ArUco, seule la plus
        proche le prend — l'autre affiche [?].
        """
        import cv2
        import numpy as np
        import time
        from modele.detecteur_couleur import (
            get_modele,
            detecter_couleur_colonne as _dc,
            _detecter_aruco,
        )

        COLORS = {
            'red':    (0, 0, 255),
            'orange': (0, 140, 255),
            'green':  (0, 255, 0),
            'off':    (120, 120, 120),
        }

        def generate():
            mdl = get_modele()

            while True:
                fb = self.cam_mgr.get_frame(id_camera)

                if fb and mdl:
                    buf   = np.frombuffer(fb, dtype=np.uint8)
                    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)

                    if frame is not None:

                        # Détection des marqueurs ArUco dans la frame
                        aruco_list = _detecter_aruco(frame, draw=True)

                        # Détection YOLO — classe 0 = colonne entière uniquement
                        results = mdl(frame, verbose=False, conf=0.20)
                        boxes   = [b for b in results[0].boxes if int(b.cls[0]) == 0]

                        # ── Fix ArUco unique ───────────────────────────────────
                        # Première passe : pour chaque colonne, on cherche l'ArUco
                        # le plus proche. Si deux colonnes veulent le même ArUco,
                        # seule la plus proche le garde — l'autre repart sans ArUco.
                        aruco_pris = {}   # {aruco_id: distance_min déjà attribuée}
                        box_aruco  = {}   # {index_box: aruco_id associé}

                        for i, box in enumerate(boxes):
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cx = (x1 + x2) // 2
                            cy = (y1 + y2) // 2
                            ap, dm = None, 200  # distance max 200px — au-delà on ignore

                            for (aid, ax, ay) in aruco_list:
                                d = ((cx - ax)**2 + (cy - ay)**2)**0.5
                                if d < dm:
                                    # Prend l'ArUco seulement si personne ne l'a
                                    # déjà réclamé avec une distance plus courte
                                    if aid not in aruco_pris or d < aruco_pris[aid]:
                                        aruco_pris[aid] = d
                                        dm = d
                                        ap = aid

                            box_aruco[i] = ap

                        # Deuxième passe : dessin des annotations
                        for i, box in enumerate(boxes):
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            cx   = (x1 + x2) // 2
                            cy   = (y1 + y2) // 2
                            ap   = box_aruco.get(i)

                            # Couleur détectée par luminosité des 3 tiers
                            couleur = _dc(frame, x1, y1, x2, y2)
                            color   = COLORS.get(couleur, (255, 255, 255))

                            # Bbox de la colonne
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                            # Lignes de séparation des 3 tiers (rouge / orange / vert)
                            h_box = y2 - y1
                            h_cut = y2 - int(h_box * 0.30)
                            tiers = (h_cut - y1) // 3
                            cv2.line(frame, (x1, y1 + tiers),     (x2, y1 + tiers),     (255, 255, 255), 1)
                            cv2.line(frame, (x1, y1 + 2 * tiers), (x2, y1 + 2 * tiers), (255, 255, 255), 1)

                            # Ligne vers l'ArUco associé (si trouvé)
                            if ap is not None:
                                for (aid, ax, ay) in aruco_list:
                                    if aid == ap:
                                        cv2.line(frame, (cx, cy), (ax, ay), (0, 255, 255), 1)
                                lbl = f"colonne [ArUco#{ap}] [{couleur}] {conf:.0%}"
                            else:
                                # Pas d'ArUco proche — colonne non identifiée
                                lbl = f"colonne [?] [{couleur}] {conf:.0%}"

                            # Label au-dessus de la bbox
                            (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
                            cv2.putText(frame, lbl, (x1 + 2, y1 - 4),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

                        _, buf_out = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        fb = buf_out.tobytes()

                else:
                    # Pas de frame disponible — image de remplacement
                    img = np.zeros((360, 640, 3), dtype=np.uint8)
                    cv2.putText(img, "Connexion en cours...", (150, 180),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
                    _, buf_out = cv2.imencode('.jpg', img)
                    fb = buf_out.tobytes()

                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + fb + b'\r\n'
                time.sleep(0.1)

        self._start_camera(id_camera)
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
