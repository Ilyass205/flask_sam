# coding: utf-8
"""
modele/supervision_alerte.py

Récupération des alertes stockées en base.
"""
from modele.supervision_base import _Base


class SupervisionAlerte(_Base):

    def get_alertes(self, limite=10):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT a.id_alerte, a.date_alerte, a.type_alerte, m.nom_machine
                FROM alerte a
                JOIN machine m ON a.id_machine = m.id_machine
                ORDER BY a.date_alerte DESC
                LIMIT %s
            """, (limite,))
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[ALERTE] get_alertes : {e}")
            return []

    def get_machines_liste(self):
        """Retourne toutes les machines pour le formulaire d'ajout d'alerte."""
        try:
            cur = self._cursor()
            cur.execute("SELECT id_machine, nom_machine FROM machine ORDER BY nom_machine")
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[ALERTE] get_machines_liste : {e}")
            return []

    def ajouter_alerte(self, type_alerte, id_machine):
        """Crée une nouvelle alerte."""
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO alerte (date_alerte, type_alerte, id_machine) VALUES (NOW(), %s, %s)",
                (type_alerte, id_machine)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[ALERTE] ajouter_alerte : {e}")
            return False

    def supprimer_alerte(self, id_alerte):
        """Supprime une alerte par son ID."""
        try:
            cur = self._cursor()
            cur.execute("DELETE FROM alerte WHERE id_alerte = %s", (id_alerte,))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[ALERTE] supprimer_alerte : {e}")
            return False
