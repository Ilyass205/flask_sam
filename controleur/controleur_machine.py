# coding: utf-8
"""
controleur/controleur_machine.py
Gestion des machines — CRUD complet avec contrôle d'accès par rôle.

Rôles et droits :
    - admin      → tout (ajouter, modifier, supprimer, configurer)
    - technicien → voir + changer l'état des machines
    - superviseur→ lecture seule, aucune modification
"""

from flask import render_template, jsonify, request, session, redirect, url_for
from modele.Supervision import Supervision
from controleur.validators import (
    ValidationError,
    get_json_payload,
    normalise_int,
    normalise_string,
    validation_message,
    valide_date,
    valide_id,
    valide_nom,
)


class ControleurMachine:

    def __init__(self, appli):
        self.mysql  = appli.mysql
        self.config = appli.app.config

    def _role(self):
        """Retourne le rôle de l'utilisateur connecté."""
        return session.get('role', '')

    def _est_admin_ou_tech(self):
        """Vrai si l'utilisateur peut modifier les machines (admin ou technicien)."""
        return self._role() in ('admin', 'technicien')

    def _est_admin(self):
        """Vrai si l'utilisateur est admin (accès complet)."""
        return self._role() == 'admin'

    # ── Pages HTML ─────────────────────────────────────────────────

    def machines_config(self):
        """
        Page de configuration des machines.
        Accessible aux admin et techniciens seulement —
        les superviseurs voient uniquement le dashboard.
        """
        if not self._est_admin_ou_tech():
            return redirect(url_for('index'))

        model = Supervision(self.mysql)
        return render_template(
            "machines_config.html",
            machines=model.get_machines(),
            cameras=model.get_all_cameras(),
            emplacements=model.get_emplacements()
        )

    # ── API Machines ───────────────────────────────────────────────

    def api_get_machines(self):
        """Retourne toutes les machines — accessible à tous les rôles."""
        model    = Supervision(self.mysql)
        machines = model.get_machines()
        return jsonify(self._serialise(machines))

    def api_ajouter_machine(self):
        """
        Ajoute une nouvelle machine en BDD.
        Réservé aux admin et techniciens.
        """
        if not self._est_admin_ou_tech():
            return jsonify({"success": False, "message": "Accès refusé"}), 403

        try:
            data = get_json_payload(
                request,
                {'nom', 'type_machine', 'date_installation', 'id_emplacement', 'aruco_id'},
                {'nom', 'id_emplacement'}
            )
            nom          = normalise_string(data.get('nom'), 'nom', min_len=3, max_len=50)
            type_m       = normalise_string(data.get('type_machine', ''), 'type_machine', min_len=0, max_len=50)
            date_install = data.get('date_installation') or None
            id_empl      = normalise_int(data.get('id_emplacement'), 'id_emplacement')
            aruco_id     = normalise_int(data.get('aruco_id'), 'aruco_id', min_value=0, allow_none=True)
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_nom(nom) or not valide_id(id_empl):
            return jsonify({"success": False, "message": "Données machine invalides"}), 400
        if type_m and not valide_nom(type_m, min_len=1, max_len=50):
            return jsonify({"success": False, "message": "Type machine invalide"}), 400
        if date_install and not valide_date(date_install):
            return jsonify({"success": False, "message": "Date installation invalide"}), 400

        model  = Supervision(self.mysql)
        new_id = model.ajouter_machine(nom, type_m, date_install, id_empl, aruco_id)

        if new_id:
            return jsonify({"success": True, "id_machine": new_id})
        return jsonify({"success": False, "message": "Erreur BDD"}), 500

    def api_modifier_machine(self, id_machine):
        """
        Modifie une machine existante.
        Réservé aux admin et techniciens.
        """
        if not self._est_admin_ou_tech():
            return jsonify({"success": False, "message": "Accès refusé"}), 403

        try:
            data = get_json_payload(
                request,
                {'nom', 'type_machine', 'date_installation', 'id_emplacement', 'aruco_id'},
                {'nom', 'id_emplacement'}
            )
            nom          = normalise_string(data.get('nom'), 'nom', min_len=3, max_len=50)
            type_m       = normalise_string(data.get('type_machine', ''), 'type_machine', min_len=0, max_len=50)
            date_install = data.get('date_installation') or None
            id_empl      = normalise_int(data.get('id_emplacement'), 'id_emplacement')
            aruco_id     = normalise_int(data.get('aruco_id'), 'aruco_id', min_value=0, allow_none=True)
        except ValidationError as exc:
            return jsonify(validation_message(str(exc))), 400

        if not valide_nom(nom) or not valide_id(id_empl):
            return jsonify({"success": False, "message": "Données machine invalides"}), 400
        if type_m and not valide_nom(type_m, min_len=1, max_len=50):
            return jsonify({"success": False, "message": "Type machine invalide"}), 400
        if date_install and not valide_date(date_install):
            return jsonify({"success": False, "message": "Date installation invalide"}), 400

        model = Supervision(self.mysql)
        ok    = model.modifier_machine(id_machine, nom, type_m, date_install, id_empl, aruco_id)
        return jsonify({"success": ok})

    def api_supprimer_machine(self, id_machine):
        """
        Supprime une machine et tout ce qui y est lié (historique, alertes, associations).
        Réservé aux admins uniquement — trop destructeur pour les techniciens.
        """
        if not self._est_admin():
            return jsonify({"success": False, "message": "Accès refusé — admin requis"}), 403

        model = Supervision(self.mysql)
        ok    = model.supprimer_machine(id_machine)
        return jsonify({"success": ok})

    def api_get_emplacements(self):
        """Retourne tous les emplacements — lecture seule, accessible à tous."""
        model        = Supervision(self.mysql)
        emplacements = model.get_emplacements()
        return jsonify(self._serialise(emplacements))

    def api_get_machines_pour_alerte(self):
        """Liste simplifiée des machines pour le sélecteur d'alertes."""
        model    = Supervision(self.mysql)
        machines = model.get_machines()
        return jsonify(self._serialise(machines))

    @staticmethod
    def _serialise(rows):
        """Convertit les rows MySQL en dicts JSON-sérialisables (dates en ISO 8601)."""
        result = []
        for row in rows:
            r = dict(row)
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
            result.append(r)
        return result
