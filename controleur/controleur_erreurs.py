# coding: utf-8
"""
controleur/controleur_erreurs.py
================================
Gestion des erreurs HTTP (404, 500).

Responsabilité:
    - Handlers d'erreur pour 404 (page non trouvée)
    - Handlers d'erreur pour 500 (erreur serveur)
    - Affichage pages d'erreur personnalisées

Pourquoi séparé:
    - Gestion d'erreurs = logique isolée
    - Facilite ajout de nouveaux codes d'erreur
    - Templates erreurs/ déjà préparés
"""

import logging
from flask import jsonify, render_template, request

log = logging.getLogger('ERRORS')


class ControleurErreurs:
    """
    Contrôleur pour gestion des erreurs HTTP.
    """

    def __init__(self, appli):
        """
        Initialisation du contrôleur erreurs.
        
        Args:
            appli: Instance Application
        """
        self.mysql = appli.mysql
        self.config = appli.app.config

    # ────────────────────────────────────────────────────────────────
    # Handlers d'erreur
    # ────────────────────────────────────────────────────────────────

    def _veut_json(self):
        return request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json'

    def _reponse_erreur(self, code, message, template=None):
        if self._veut_json():
            return jsonify({"success": False, "message": message}), code
        if template:
            return render_template(template), code
        return render_template('erreurs/500.html'), code

    def erreur_400(self, e):
        return self._reponse_erreur(400, "Requête invalide")

    def erreur_403(self, e):
        return self._reponse_erreur(403, "Accès refusé")

    def erreur_404(self, e):
        """
        Handler d'erreur 404 (page non trouvée).
        
        Args:
            e: Exception Flask
        
        Retour:
            Tuple (HTML, code_HTTP)
        
        Enregistrement:
            app.register_error_handler(404, cp.erreur_404)
        
        Template:
            templates/erreurs/404.html
        """
        return self._reponse_erreur(404, "Ressource introuvable", 'erreurs/404.html')

    def erreur_405(self, e):
        return self._reponse_erreur(405, "Méthode non autorisée")

    def erreur_500(self, e):
        """
        Handler d'erreur 500 (erreur serveur).
        
        Args:
            e: Exception Flask
        
        Retour:
            Tuple (HTML, code_HTTP)
        
        Enregistrement:
            app.register_error_handler(500, cp.erreur_500)
        
        Template:
            templates/erreurs/500.html
        """
        log.exception("Erreur serveur non gérée")
        return self._reponse_erreur(500, "Erreur interne du serveur", 'erreurs/500.html')
