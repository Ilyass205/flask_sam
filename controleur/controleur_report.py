# coding: utf-8
"""
controleur/controleur_report.py
===============================
Gestion et génération des rapports (CSV, PDF, HTML).

Responsabilité:
    - Page de rapports
    - Génération rapports CSV (complet, événements, états, alertes)
    - Génération rapport PDF
    - Aperçu HTML du rapport

Pourquoi séparé:
    - Rapports = logique métier complexe
    - Dépend de modele/supervision_rapport.py
    - Isolé pour clarté et testabilité
"""

from flask import render_template, Response
from modele.Supervision import Supervision
from modele.supervision_rapport import (
    generer_csv_evenements,
    generer_csv_etats,
    generer_csv_alertes,
    generer_csv_complet,
    generer_pdf_rapport,
    generer_html_rapport
)
from controleur.validators import valide_id
import datetime


class ControleurReport:
    """
    Contrôleur pour gestion des rapports.
    """

    def __init__(self, appli):
        """
        Initialisation du contrôleur rapport.
        
        Args:
            appli: Instance Application
        """
        self.mysql = appli.mysql
        self.config = appli.app.config

    # ────────────────────────────────────────────────────────────────
    # Route HTML (page)
    # ────────────────────────────────────────────────────────────────

    def rapports(self):
        """
        Affiche la page de gestion des rapports.
        
        Retour:
            Rendu de rapports.html
        
        Logique:
            - Affiche liens vers différents exports
            - Liens directs vers PDF, CSV, aperçu
        
        Route: GET /rapports
        
        Template: templates/rapports.html
            Affiche:
            - Boutons téléchargement CSV/PDF
            - Aperçu rapport HTML
        
        Utilisateur: Tous (auth)
        """
        return render_template("rapports.html")

    # ────────────────────────────────────────────────────────────────
    # Récupération données rapport
    # ────────────────────────────────────────────────────────────────

    def _rapport_data(self):
        """
        Récupère l'ensemble des données pour un rapport.
        
        Retour:
            dict avec clés: evenements, etats, alertes, machines
        
        Logique:
            - Requête unique en BDD (performance)
            - Retour prêt pour tous les générateurs
        
        Utilisé par:
            - rapport_csv_complet
            - rapport_csv_evenements
            - rapport_pdf
            - rapport_apercu
        """
        model = Supervision(self.mysql)
        return model.get_donnees_rapport()

    # ────────────────────────────────────────────────────────────────
    # Exports CSV
    # ────────────────────────────────────────────────────────────────

    def rapport_csv_complet(self):
        """
        Génère un rapport CSV complet.
        
        Contenu:
            - Tous les événements
            - Tous les états
            - Tous les alertes
        
        Retour:
            Response avec fichier CSV (download)
        
        Route: GET /rapports/csv/complet
        
        Fichier:
            rapport_complet_YYYYMMDD_HHMM.csv
        
        Format:
            CSV UTF-8 avec BOM (compatible Excel)
        
        Logique:
            1. Récupérer données rapport
            2. Générer CSV via supervision_rapport
            3. Retourner Response avec headers download
        """
        content = generer_csv_complet(self._rapport_data())
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        
        return Response(
            content,
            mimetype="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": f"attachment; filename=rapport_complet_{date}.csv"
            }
        )

    def rapport_csv_evenements(self):
        """
        Génère un CSV contenant uniquement les événements.
        
        Contenu:
            - Tous les changements d'état (couleur)
            - Date, machine, couleur
        
        Retour:
            Response avec fichier CSV
        
        Route: GET /rapports/csv/evenements
        
        Fichier:
            evenements_YYYYMMDD_HHMM.csv
        
        Utilité:
            - Analyse trends d'utilisation machines
            - Maintenance (fréquence transitions)
        """
        data = self._rapport_data()
        content = generer_csv_evenements(data.get("evenements", []))
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        
        return Response(
            content,
            mimetype="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": f"attachment; filename=evenements_{date}.csv"
            }
        )

    def rapport_csv_etats(self):
        """
        Génère un CSV contenant les états (dernier pour chaque machine).
        
        Contenu:
            - État actuel de chaque machine
            - Timestamp dernier changement
        
        Retour:
            Response avec fichier CSV
        
        Route: GET /rapports/csv/etats
        
        Fichier:
            etats_machines_YYYYMMDD_HHMM.csv
        
        Utilité:
            - Snapshot état parc machines
            - Export pour suivi budget maintenance
        """
        data = self._rapport_data()
        content = generer_csv_etats(data.get("etats", []))
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        
        return Response(
            content,
            mimetype="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": f"attachment; filename=etats_machines_{date}.csv"
            }
        )

    def rapport_csv_alertes(self):
        """
        Génère un CSV contenant les alertes.
        
        Contenu:
            - Toutes les alertes enregistrées
            - Date, type, machine
        
        Retour:
            Response avec fichier CSV
        
        Route: GET /rapports/csv/alertes
        
        Fichier:
            alertes_YYYYMMDD_HHMM.csv
        
        Utilité:
            - Analyse problèmes machines
            - Maintenance préventive
            - Audit incidents
        """
        data = self._rapport_data()
        content = generer_csv_alertes(data.get("alertes", []))
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        
        return Response(
            content,
            mimetype="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": f"attachment; filename=alertes_{date}.csv"
            }
        )

    # ────────────────────────────────────────────────────────────────
    # Export PDF
    # ────────────────────────────────────────────────────────────────

    def rapport_pdf(self):
        """
        Génère un rapport PDF complet.
        
        Contenu:
            - Données et graphiques complets
            - Format PDF professionnel
        
        Retour:
            Response avec fichier PDF (download)
        
        Route: GET /rapports/pdf
        
        Fichier:
            rapport_YYYYMMDD_HHMM.pdf
        
        Dépendances:
            - modele/supervision_rapport.py (generer_pdf_rapport)
            - Peut nécessiter reportlab ou weasyprint
        
        Logique:
            1. Récupérer données rapport
            2. Générer PDF via supervision_rapport
            3. Retourner Response avec mimetype PDF
        """
        content, mime, ext = generer_pdf_rapport(self._rapport_data())
        date = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        
        return Response(
            content,
            mimetype=mime,
            headers={
                "Content-Disposition": f"attachment; filename=rapport_{date}{ext}"
            }
        )

    # ────────────────────────────────────────────────────────────────
    # Aperçu HTML
    # ────────────────────────────────────────────────────────────────

    def rapport_apercu(self):
        """
        Affiche un aperçu HTML du rapport.
        
        Retour:
            Rendu HTML du rapport (pas de download)
        
        Route: GET /rapports/apercu
        
        Logique:
            1. Récupérer données rapport
            2. Générer HTML formaté
            3. Afficher dans navigateur (pas de download)
        
        Utilité:
            - Prévisualisation avant export
            - Vérification données
            - Partage par copier/coller
        
        Note:
            - Peut être lente si beaucoup de données
            - À optimiser avec pagination si besoin
        """
        return generer_html_rapport(self._rapport_data())
