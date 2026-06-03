# coding: utf-8
from flask import jsonify, render_template
from modele.Supervision import Supervision


class ControleurStats:

    def __init__(self, appli):
        self.mysql = appli.mysql

    def api_stats_dashboard(self):
        model = Supervision(self.mysql)
        return jsonify(model.get_stats_dashboard())

    def api_stats_etats(self):
        model = Supervision(self.mysql)
        return jsonify(model.get_stats_etats_7j())

    def api_stats_evenements(self):
        model = Supervision(self.mysql)
        return jsonify(model.get_stats_evenements_par_jour())

    def api_stats_machines(self):
        model = Supervision(self.mysql)
        return jsonify(model.get_stats_par_machine())

    def afficher_stats(self):
        return render_template("stats.html")
