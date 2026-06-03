# coding: utf-8
"""
controleur/controleur_event.py
==============================
Gestion des événements (changements d'état) et alertes.

Responsabilité:
    - Lecture de l'état actuel d'une machine
    - Insertion de nouveaux événements
    - Lecture des alertes
    - Pages historique et alertes

Nota bene:
    - Événement = changement d'état (couleur)
    - Alerte = situation anormale (arrêt inattendu, etc)
    - SANS détection couleur (ça venait du detecteur supprimé)
"""

from flask import render_template, jsonify, request
from modele.Supervision import Supervision
from controleur.validators import valide_id


class ControleurEvent:
    """
    Contrôleur pour gestion des événements et alertes.
    """

    def __init__(self, appli):
        """
        Initialisation du contrôleur événement.
        
        Args:
            appli: Instance Application
        """
        self.mysql = appli.mysql
        self.config = appli.app.config

    # ────────────────────────────────────────────────────────────────
    # Routes HTML (pages)
    # ────────────────────────────────────────────────────────────────

    def historique(self):
        """
        Affiche l'historique global de tous les événements.
        
        Retour:
            Rendu de historique.html
        
        Logique:
            1. Récupérer tous les événements (ordered by date DESC)
            2. Rendre template avec liste
        
        Route: GET /historique
        
        Template: templates/historique.html
            Affiche:
            - Table de tous les événements (date, machine, couleur/état)
            - Filtres optionnels (date, machine)
        
        Utilisateur: Tous (auth)
        """
        model = Supervision(self.mysql)
        evenements = model.get_historique_global()
        
        return render_template("historique.html", evenements=evenements)

    def alertes(self):
        """
        Affiche l'historique des alertes.
        
        Retour:
            Rendu de alertes.html
        
        Logique:
            1. Récupérer dernières alertes (limit=50)
            2. Rendre template
        
        Route: GET /alertes
        
        Template: templates/alertes.html
            Affiche:
            - Table des alertes (date, type, machine)
            - Types: "Arrêt inattendu", "Maintenance", etc
        
        Utilisateur: Tous (auth)
        """
        model    = Supervision(self.mysql)
        alertes  = model.get_alertes(limite=50)
        machines = model.get_machines_liste()
        return render_template("alertes.html", alertes=alertes, machines=machines)

    # ────────────────────────────────────────────────────────────────
    # API État machine
    # ────────────────────────────────────────────────────────────────

    def api_get_etat_machine(self, id_machine):
        """
        Récupère l'état actuel d'une machine.
        
        Args:
            id_machine: ID de la machine
        
        Retour:
            JSON avec dernier événement (couleur, timestamp)
        
        Route: GET /api/etat/<id_machine>
        
        Exemple réponse:
            {
              "id_machine": 1,
              "nom_couleur": "Vert",
              "etat_couleur": "marche",
              "horodatage_evenement": "2026-03-11T13:00:00"
            }
        
        Ou si aucun événement:
            {
              "nom_couleur": "Inconnu",
              "etat_couleur": "inconnu",
              "horodatage_evenement": null
            }
        
        Logique:
            1. Récupérer dernier événement pour cette machine
            2. Inclure couleur et timestamp
            3. Convertir datetime en ISO 8601
        """
        model = Supervision(self.mysql)
        etat = model.get_etat_machine(id_machine)
        
        if etat:
            r = dict(etat)
            # Convertir datetime en ISO 8601 pour JSON
            if hasattr(r.get('horodatage_evenement'), 'isoformat'):
                r['horodatage_evenement'] = r['horodatage_evenement'].isoformat()
            return jsonify(r)
        
        # Pas d'événement: retourner défaut
        return jsonify({
            "nom_couleur": "Inconnu",
            "etat_couleur": "inconnu",
            "horodatage_evenement": None
        })

    # ────────────────────────────────────────────────────────────────
    # API Événements (insertion)
    # ────────────────────────────────────────────────────────────────

    def api_inserer_evenement(self):
        """
        Insère un nouvel événement (changement d'état).
        
        Retour:
            JSON {"success": True/False}
        
        Route: POST /api/evenements
        
        Body JSON requis:
            {
              "id_machine": 1,
              "id_couleur": 3     (1=Rouge, 2=Orange, 3=Vert)
            }
        
        Couleurs:
            1 = Rouge (arrêt)
            2 = Orange (maintenance)
            3 = Vert (marche normal)
        
        Logique:
            1. Vérifier paramètres (id_machine, id_couleur)
            2. Insérer dans table 'evenement' avec timestamp NOW()
            3. Retourner succès/erreur
        
        Validation:
            - id_machine et id_couleur obligatoires
            - id_couleur doit exister
        
        Erreur:
            - 400 si paramètres manquants
            - 500 si erreur BDD
        
        Note:
            - Timestamp créé côté BDD (NOT NULL DEFAULT NOW())
            - Pas d'horodatage client (éviter sync issues)
        """
        data = request.get_json(silent=True) or {}
        id_machine = data.get('id_machine')
        id_couleur = data.get('id_couleur')
        
        # Vérifier paramètres
        if not id_machine or not id_couleur:
            return jsonify({
                "success": False,
                "message": "id_machine et id_couleur requis"
            }), 400
        
        # Insérer en BDD
        model = Supervision(self.mysql)
        ok = model.inserer_evenement(id_machine, id_couleur)
        
        return jsonify({"success": ok})

    # ────────────────────────────────────────────────────────────────
    # API Alertes (lecture seule)
    # ────────────────────────────────────────────────────────────────

    def api_get_alertes(self):
        """
        Récupère toutes les alertes.
        
        Retour:
            JSON array d'alertes
        
        Route: GET /api/alertes
        
        Exemple réponse:
            [
              {
                "id_alerte": 1,
                "date_alerte": "2025-03-01T09:50:00",
                "type_alerte": "Arrêt inattendu",
                "id_machine": 2
              }
            ]
        
        Types d'alertes:
            - "Arrêt inattendu"
            - "Maintenance préventive"
            - "Maintenance longue"
            - "Redémarrage après panne"
            - Autres (défini en BDD)
        
        Logique:
            - Lecture seule en BDD
            - Conversion datetime → ISO 8601
        """
        model = Supervision(self.mysql)
        alertes = model.get_alertes()
        
        return jsonify(self._serialise(alertes))

    # ────────────────────────────────────────────────────────────────
    # Helper: Sérialisation
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialise(rows):
        """
        Convertit les rows MySQL en dicts JSON-compatibles.
        
        Args:
            rows: list de Row objects
        
        Retour:
            list de dicts avec dates en isoformat
        """
        result = []
        for row in rows:
            r = dict(row)
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
            result.append(r)
        return result

    def api_get_historique_machine(self, id_machine):
        model = Supervision(self.mysql)
        rows  = model.get_historique_machine(id_machine, limite=20)
        result = []
        for row in rows:
            r = dict(row)
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
            result.append(r)
        from flask import jsonify
        return jsonify(result)

    def api_ajouter_alerte(self):
        """API POST /api/alertes/ajouter — Crée une nouvelle alerte."""
        from flask import request, jsonify
        data       = request.get_json(silent=True) or {}
        type_alerte = data.get('type_alerte', '').strip()
        id_machine  = data.get('id_machine')
        if not type_alerte or not id_machine:
            return jsonify({"success": False, "message": "type et machine requis"}), 400
        model = Supervision(self.mysql)
        ok    = model.ajouter_alerte(type_alerte, int(id_machine))
        return jsonify({"success": ok})

    def api_supprimer_alerte(self, id_alerte):
        """API DELETE /api/alertes/<id> — Supprime une alerte."""
        from flask import jsonify
        model = Supervision(self.mysql)
        ok    = model.supprimer_alerte(id_alerte)
        return jsonify({"success": ok})

    def api_get_machines_pour_alerte(self):
        """API GET /api/machines/liste — Liste des machines pour le formulaire."""
        from flask import jsonify
        model    = Supervision(self.mysql)
        machines = model.get_machines_liste()
        return jsonify([dict(m) for m in machines])
