# coding: utf-8
from modele.supervision_base import _Base


class SupervisionStats(_Base):

    def get_stats_dashboard(self):
        """Retourne les stats pour le dashboard : nb cams, machines, alertes 24h, TRS."""
        try:
            cur = self._cursor()
            cur.execute("SELECT COUNT(*) AS nb FROM camera")
            nb_cams = cur.fetchone()['nb']

            cur.execute("SELECT COUNT(*) AS nb FROM machine")
            nb_machines = cur.fetchone()['nb']

            cur.execute("""
                SELECT COUNT(*) AS nb FROM alerte
                WHERE date_alerte >= NOW() - INTERVAL 24 HOUR
            """)
            nb_alertes = cur.fetchone()['nb']

            # TRS = % du temps en marche sur les 7 derniers jours
            cur.execute("""
                SELECT c.etat_couleur, COUNT(*) AS nb
                FROM evenement e
                JOIN couleur c ON e.id_couleur = c.id_couleur
                WHERE e.horodatage_evenement >= NOW() - INTERVAL 7 DAY
                GROUP BY c.etat_couleur
            """)
            rows  = cur.fetchall()
            total = sum(r['nb'] for r in rows)
            marche = next((r['nb'] for r in rows if r['etat_couleur'] == 'marche'), 0)
            trs   = round(marche / total * 100) if total > 0 else 0

            cur.close()
            return {
                'nb_cameras':  nb_cams,
                'nb_machines': nb_machines,
                'nb_alertes':  nb_alertes,
                'trs':         trs,
            }
        except Exception as e:
            print(f"[STATS] get_stats_dashboard : {e}")
            return {'nb_cameras': 0, 'nb_machines': 0, 'nb_alertes': 0, 'trs': 0}

    def get_stats_etats_7j(self):
        """Répartition des états sur 7 jours (pour graphique camembert)."""
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT c.nom_couleur, c.etat_couleur, COUNT(*) AS nb
                FROM evenement e
                JOIN couleur c ON e.id_couleur = c.id_couleur
                WHERE e.horodatage_evenement >= NOW() - INTERVAL 7 DAY
                GROUP BY c.id_couleur, c.nom_couleur, c.etat_couleur
            """)
            res = cur.fetchall()
            cur.close()
            return [dict(r) for r in res]
        except Exception as e:
            print(f"[STATS] get_stats_etats_7j : {e}")
            return []

    def get_stats_evenements_par_jour(self):
        """Nb d'événements par jour sur 14 jours (pour graphique courbe)."""
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT DATE(horodatage_evenement) AS jour, COUNT(*) AS nb
                FROM evenement
                WHERE horodatage_evenement >= NOW() - INTERVAL 14 DAY
                GROUP BY DATE(horodatage_evenement)
                ORDER BY jour ASC
            """)
            res = cur.fetchall()
            cur.close()
            return [{'jour': str(r['jour']), 'nb': r['nb']} for r in res]
        except Exception as e:
            print(f"[STATS] get_stats_evenements_par_jour : {e}")
            return []

    def get_stats_par_machine(self):
        """TRS par machine sur 7 jours (pour graphique barres)."""
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.nom_machine,
                    SUM(CASE WHEN c.etat_couleur='marche'      THEN 1 ELSE 0 END) AS marche,
                    SUM(CASE WHEN c.etat_couleur='arret'       THEN 1 ELSE 0 END) AS arret,
                    SUM(CASE WHEN c.etat_couleur='maintenance' THEN 1 ELSE 0 END) AS maintenance,
                    COUNT(*) AS total
                FROM evenement e
                JOIN machine m ON e.id_machine = m.id_machine
                JOIN couleur c ON e.id_couleur = c.id_couleur
                WHERE e.horodatage_evenement >= NOW() - INTERVAL 7 DAY
                GROUP BY m.id_machine, m.nom_machine
                ORDER BY m.id_machine
            """)
            res = cur.fetchall()
            cur.close()
            result = []
            for r in res:
                trs = round(r['marche'] / r['total'] * 100) if r['total'] > 0 else 0
                result.append({
                    'nom_machine': r['nom_machine'],
                    'marche':      r['marche'],
                    'arret':       r['arret'],
                    'maintenance': r['maintenance'],
                    'trs':         trs,
                })
            return result
        except Exception as e:
            print(f"[STATS] get_stats_par_machine : {e}")
            return []
