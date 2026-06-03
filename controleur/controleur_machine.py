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
from controleur.validators import valide_nom, valide_id


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

        data         = request.get_json(silent=True) or {}
        nom          = data.get('nom', '').strip()
        type_m       = data.get('type_machine', '').strip()
        date_install = data.get('date_installation') or None
        id_empl      = data.get('id_emplacement')
        # aruco_id peut être None si non renseigné — c'est ok
        aruco_raw    = data.get('aruco_id')
        aruco_id     = int(aruco_raw) if aruco_raw not in (None, '', 'null') else None

        if not nom or not id_empl:
            return jsonify({"success": False, "message": "nom et id_emplacement requis"}), 400

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

        data         = request.get_json(silent=True) or {}
        nom          = data.get('nom', '').strip()
        type_m       = data.get('type_machine', '').strip()
        date_install = data.get('date_installation') or None
        id_empl      = data.get('id_emplacement')
        aruco_raw    = data.get('aruco_id')
        aruco_id     = int(aruco_raw) if aruco_raw not in (None, '', 'null') else None

        if not nom or not id_empl:
            return jsonify({"success": False, "message": "nom et id_emplacement requis"}), 400

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