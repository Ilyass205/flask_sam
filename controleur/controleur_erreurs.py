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

from flask import render_template


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
        return render_template('erreurs/404.html'), 404

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
        return render_template('erreurs/500.html'), 500
