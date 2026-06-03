# coding: utf-8
"""
controleur/controleur_auth.py
Authentification, sessions et gestion des utilisateurs.

Rôles et droits :
    - admin      → tout (CRUD users, config caméras, config machines, tout voir)
    - technicien → voir cams + changer état machines (pas de config)
    - superviseur→ lecture seule — dashboard, historique, rapports uniquement
"""

from flask import render_template, request, session, redirect, url_for, jsonify
from modele.supervision_auth import a_permission
from controleur.validators import (
    ValidationError,
    get_json_payload,
    normalise_string,
    require_choice,
    validation_message,
    valide_login,
    valide_mot_de_passe,
)


class ControleurAuth:

    def __init__(self, appli):
        self.mysql  = appli.mysql
        self.config = appli.app.config

    def _role(self):
        """Retourne le rôle de l'utilisateur connecté depuis la session."""
        return session.get('role', '')

    def _check(self, perm):
        """Vérifie si l'utilisateur a la permission demandée."""
        return a_permission(self._role(), perm)

    # ── Login / Logout ─────────────────────────────────────────────

    def afficher_login(self):
        return render_template("login.html")

    def traiter_login(self):
        """
        Traite le formulaire de connexion.
        Si les credentials sont bons → session créée et redirection vers le dashboard.
        Sinon → page login avec message d'erreur.
        """
        champs_autorises = {'login', 'password'}
        if set(request.form.keys()) - champs_autorises:
            return render_template("login.html", erreur="Formulaire invalide"), 400

        identifiant  = request.form.get("login", "").strip()
        mot_de_passe = request.form.get("password", "")
        if not valide_login(identifiant) or not mot_de_passe:
            return render_template("login.html", erreur="Identifiants incorrects"), 400
        print(f"[LOGIN] login='{identifiant}'")

        from modele.Supervision import Supervision
        res = Supervision(self.mysql).test_login(identifiant, mot_de_passe)
        print(f"[LOGIN] res={res}")

        if res:
            session.permanent      = True
            session['utilisateur'] = res['login_user']
            session['role']        = res['role_user']
            session['id_user']     = res['id_user']  # utile pour éviter de se supprimer soi-même
            print(f"[LOGIN] OK role={res['role_user']} → /index")
            return redirect(url_for('index'))

        print(f"[LOGIN] ECHEC")
        return render_template("login.html", erreur="Identifiants incorrects")

    def deconnexion(self):
        session.clear()
        return redirect(url_for('afficher_login'))

    def deconnexionb(self):
        return self.deconnexion()

    def test_before_request(self, routes_exceptions):
        """
        Vérifié avant chaque requête — redirige vers login si pas connecté.
        Les routes publiques (login, static...) sont exemptées.
        """
        from flask import request as req
        if req.endpoint and req.endpoint not in routes_exceptions:
            if not session.get("utilisateur"):
                return redirect(url_for('afficher_login'))

    # ── Gestion des utilisateurs (admin seulement) ─────────────────

    def afficher_users(self):
        """
        Page de gestion des utilisateurs.
        Accessible aux admins uniquement.
        """
        if not self._check('tout'):
            return redirect(url_for('index'))
        from modele.Supervision import Supervision
        users = Supervision(self.mysql).get_users()
        return render_template("users.html", users=users)

    def api_get_users(self):
        """Liste tous les utilisateurs — admin uniquement."""
        if not self._check('tout'):
            return jsonify({"success": False, "message": "Accès refusé"}), 403
        from modele.Supervision import Supervision
        users = Supervision(self.mysql).get_users()
        return jsonify([dict(u) for u in users])

    def api_ajouter_user(self):
        """
        Crée un nouvel utilisateur avec mot de passe hashé.
        Admin uniquement.
        """
        if not self._check('tout'):
            return jsonify({"success": False, "message": "Accès refusé"}), 403

        try:
            data  = get_json_payload(request, {'login', 'mdp', 'role'}, {'login', 'mdp'})
            login = normalise_string(data.get('login'), 'login', min_len=3, max_len=50)
            mdp   = normalise_string(data.get('mdp'), 'mdp', min_len=8, max_len=128)
            role  = require_choice(data.get('role', 'technicien'), 'role', ['admin', 'technicien', 'superviseur'])
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_login(login):
            return jsonify({"success": False, "message": "Login invalide"}), 400
        if not valide_mot_de_passe(mdp):
            return jsonify({"success": False, "message": "Mot de passe invalide"}), 400

        from modele.Supervision import Supervision
        ok = Supervision(self.mysql).ajouter_user(login, mdp, role)
        return jsonify({"success": ok})

    def api_modifier_user(self, id_user):
        """
        Modifie un utilisateur existant.
        Si mdp est vide → le mot de passe reste inchangé.
        Admin uniquement.
        """
        if not self._check('tout'):
            return jsonify({"success": False, "message": "Accès refusé"}), 403

        try:
            data  = get_json_payload(request, {'login', 'role', 'mdp'}, {'login'})
            login = normalise_string(data.get('login'), 'login', min_len=3, max_len=50)
            role  = require_choice(data.get('role', 'technicien'), 'role', ['admin', 'technicien', 'superviseur'])
            mdp_raw = data.get('mdp')
            mdp = None if mdp_raw in (None, '') else normalise_string(mdp_raw, 'mdp', min_len=8, max_len=128)
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_login(login):
            return jsonify({"success": False, "message": "Login invalide"}), 400
        if mdp is not None and not valide_mot_de_passe(mdp):
            return jsonify({"success": False, "message": "Mot de passe invalide"}), 400

        from modele.Supervision import Supervision
        ok = Supervision(self.mysql).modifier_user(id_user, login, role, mdp)
        return jsonify({"success": ok})

    def api_supprimer_user(self, id_user):
        """
        Supprime un utilisateur.
        Impossible de supprimer son propre compte.
        Admin uniquement.
        """
        if not self._check('tout'):
            return jsonify({"success": False, "message": "Accès refusé"}), 403

        # Sécurité : on ne peut pas supprimer son propre compte
        if str(id_user) == str(session.get('id_user')):
            return jsonify({"success": False, "message": "Impossible de supprimer son propre compte"}), 400

        from modele.Supervision import Supervision
        ok = Supervision(self.mysql).supprimer_user(id_user)
        return jsonify({"success": ok})
