# coding: utf-8
"""
modele/supervision_evenement.py

Gestion des événements, états machines et historique.
"""
from modele.supervision_base import _Base


class SupervisionEvenement(_Base):

    def get_etat_machine(self, id_machine):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT c.nom_couleur, c.etat_couleur, ev.horodatage_evenement
                FROM evenement ev
                JOIN couleur c ON ev.id_couleur = c.id_couleur
                WHERE ev.id_machine = %s
                ORDER BY ev.horodatage_evenement DESC
                LIMIT 1
            """, (id_machine,))
            res = cur.fetchone()
            cur.close()
            return res
        except Exception as e:
            print(f"[EVNT] get_etat_machine({id_machine}) : {e}")
            return None

    def get_historique_machine(self, id_machine, limite=20):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT ev.horodatage_evenement, c.nom_couleur, c.etat_couleur
                FROM evenement ev
                JOIN couleur c ON ev.id_couleur = c.id_couleur
                WHERE ev.id_machine = %s
                ORDER BY ev.horodatage_evenement DESC
                LIMIT %s
            """, (id_machine, limite))
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[EVNT] get_historique_machine({id_machine}) : {e}")
            return []

    def get_historique_global(self, limite=100):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT ev.id_evenement, ev.horodatage_evenement,
                       m.nom_machine, m.type_machine,
                       c.nom_couleur, c.etat_couleur
                FROM evenement ev
                JOIN machine m ON ev.id_machine = m.id_machine
                JOIN couleur c ON ev.id_couleur = c.id_couleur
                ORDER BY ev.horodatage_evenement DESC
                LIMIT %s
            """, (limite,))
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[EVNT] get_historique_global : {e}")
            return []

    def inserer_evenement(self, id_machine, id_couleur):
        """Appelé par le DetecteurCouleur (détection vidéo automatique)."""
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO evenement (horodatage_evenement, id_machine, id_couleur) "
                "VALUES (NOW(), %s, %s)",
                (id_machine, id_couleur)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[EVNT] inserer_evenement : {e}")
            return False
