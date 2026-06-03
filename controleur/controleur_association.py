# coding: utf-8
"""
controleur/controleur_association.py
====================================
Gestion des associations caméra-machine.

Responsabilité:
    - Lier/délier caméras et machines
    - API pour gérer les associations
    - Gestion du démarrage de captures lors d'une association

Pourquoi séparé:
    - Logique spécifique (association M-to-M)
    - Communique avec CameraControleur et MachineControleur
    - Isolé pour clarté
"""

from flask import jsonify, request
from modele.Supervision import Supervision
from controleur.validators import (
    ValidationError,
    get_json_payload,
    normalise_int,
    validation_message,
    valide_id,
)


class ControleurAssociation:
    """
    Contrôleur pour gestion des associations caméra-machine.
    """

    def __init__(self, appli):
        """
        Initialisation du contrôleur association.
        
        Args:
            appli: Instance Application
        """
        self.mysql = appli.mysql
        self.config = appli.app.config
        self.cam_mgr = appli.cam_mgr

    # ────────────────────────────────────────────────────────────────
    # API Associations
    # ────────────────────────────────────────────────────────────────

    def api_ajouter_association(self):
        """
        Ajoute une association caméra-machine.
        
        Retour:
            JSON {"success": True/False, "message": "..."}
        
        Route: POST /api/associations
        
        Body JSON requis:
            {
              "id_camera": 1,
              "id_machine": 1
            }
        
        Logique:
            1. Vérifier paramètres obligatoires
            2. Insérer association en BDD
            3. Démarrer le thread de capture
        
        Erreur:
            - 400 si paramètres manquants
            - 500 si erreur BDD (ex: doublon)
        
        Après création:
            - La caméra commence à streamer immédiatement
            - Les événements de la machine seront enregistrés
        """

        from flask import session
        if session.get('role') not in ('admin', 'technicien'):
            return jsonify({"success": False, "message": "Accès refusé"}), 403
        try:
            data = get_json_payload(request, {'id_camera', 'id_machine'}, {'id_camera', 'id_machine'})
            id_camera = normalise_int(data.get('id_camera'), 'id_camera')
            id_machine = normalise_int(data.get('id_machine'), 'id_machine')
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_id(id_camera) or not valide_id(id_machine):
            return jsonify({"success": False, "message": "IDs invalides"}), 400
        
        # Ajouter association en BDD
        model = Supervision(self.mysql)
        ok = model.ajouter_association(id_camera, id_machine)
        
        if ok:
            # Démarrer le thread de capture
            self._start_camera_capture(id_camera)
            return jsonify({
                "success": True,
                "message": "Association créée"
            })
        
        # Erreur (probablement doublon)
        return jsonify({
            "success": False,
            "message": "Erreur BDD (association existante ?)"
        }), 500

    def api_supprimer_association(self, id_camera, id_machine):
        """
        Supprime une association caméra-machine.
        
        Args:
            id_camera: ID de la caméra
            id_machine: ID de la machine
        
        Retour:
            JSON {"success": True/False}
        
        Route: DELETE /api/associations/<id_camera>/<id_machine>
        
        Logique:
            1. Supprimer l'association en BDD
            2. Si succès: arrêter le thread de capture
        
        Note:
            - Arrêt du thread seulement si suppression réussie
            - Évite arrêter un thread "bon" par erreur
        """
        from flask import session
        if session.get('role') not in ('admin', 'technicien'):
            return jsonify({"success": False, "message": "Accès refusé"}), 403

        model = Supervision(self.mysql)
        ok = model.supprimer_association(id_camera, id_machine)
        
        if ok:
            # Arrêter le thread de capture (cleanup)
            self.cam_mgr.stop(id_camera)
        
        return jsonify({"success": ok})

    # ────────────────────────────────────────────────────────────────
    # Helper: Démarrage caméra
    # ────────────────────────────────────────────────────────────────

    def _start_camera_capture(self, id_camera):
        """
        Démarre le thread de capture pour une caméra.
        
        Args:
            id_camera: ID de la caméra
        
        Logique:
            1. Récupérer données caméra (IP, proto)
            2. Construire URL RTSP
            3. Démarrer CameraManager
        
        Thread-safety:
            - CameraManager gère les locks
            - Plusieurs appels = idempotent (si déjà lancé, ne fait rien)
        
        Voir:
            - CameraControleur._start_camera (logique identique)
        """
        model = Supervision(self.mysql)
        camera = model.get_camera(id_camera)
        
        if not camera or not camera.get('ip_camera'):
            return
        
        source = camera['ip_camera']
        
        # Construire URL RTSP si nécessaire
        if not source.startswith('rtsp://') and not source.startswith('http'):
            user = self.config.get('DEFAULT_RTSP_USER', 'admin')
            pwd = self.config.get('DEFAULT_RTSP_PASS', '')
            source = f"rtsp://{user}:{pwd}@{source}:554/h264Preview_01_main"
        
        # Démarrer le thread
        self.cam_mgr.start(id_camera, source)
