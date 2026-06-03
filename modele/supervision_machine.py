# coding: utf-8
"""
modele/supervision_machine.py
Accès aux données des machines — CRUD complet.
"""
from modele.supervision_base import _Base


class SupervisionMachine(_Base):

    def get_machines(self):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.id_machine, m.nom_machine, m.type_machine,
                       m.date_installation_machine, m.id_emplacement, m.aruco_id,
                       e.section_emplacement
                FROM machine m
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                ORDER BY m.id_machine
            """)
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[MACHINE] get_machines : {e}")
            return []

    def get_machine(self, id_machine):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.id_machine, m.nom_machine, m.type_machine,
                       m.date_installation_machine, m.id_emplacement, m.aruco_id,
                       e.section_emplacement
                FROM machine m
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                WHERE m.id_machine = %s
            """, (id_machine,))
            res = cur.fetchone()
            cur.close()
            return res
        except Exception as e:
            print(f"[MACHINE] get_machine({id_machine}) : {e}")
            return None

    def get_machine_par_camera(self, id_camera):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.id_machine, m.nom_machine, m.type_machine,
                       e.section_emplacement
                FROM machine_camera_association mca
                JOIN machine m ON mca.id_machine = m.id_machine
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                WHERE mca.id_camera = %s
                LIMIT 1
            """, (id_camera,))
            res = cur.fetchone()
            cur.close()
            return res
        except Exception as e:
            print(f"[MACHINE] get_machine_par_camera({id_camera}) : {e}")
            return None

    def get_machines_par_camera(self, id_camera):
        """Retourne TOUTES les machines associées à une caméra (pas juste la première)."""
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.id_machine, m.nom_machine, m.type_machine,
                       m.aruco_id, e.section_emplacement
                FROM machine_camera_association mca
                JOIN machine m ON mca.id_machine = m.id_machine
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                WHERE mca.id_camera = %s
                ORDER BY m.id_machine
            """, (id_camera,))
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[MACHINE] get_machines_par_camera({id_camera}) : {e}")
            return []

    def ajouter_machine(self, nom, type_m, date_install, id_emplacement, aruco_id=None):
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO machine (nom_machine, type_machine, "
                "date_installation_machine, id_emplacement, aruco_id) "
                "VALUES (%s,%s,%s,%s,%s)",
                (nom, type_m, date_install, id_emplacement, aruco_id)
            )
            self._commit()
            new_id = cur.lastrowid
            cur.close()
            return new_id
        except Exception as e:
            print(f"[MACHINE] ajouter_machine : {e}")
            return None

    def modifier_machine(self, id_machine, nom, type_m, date_install, id_emplacement, aruco_id=None):
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE machine SET nom_machine=%s, type_machine=%s, "
                "date_installation_machine=%s, id_emplacement=%s, aruco_id=%s "
                "WHERE id_machine=%s",
                (nom, type_m, date_install, id_emplacement, aruco_id, id_machine)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[MACHINE] modifier_machine({id_machine}) : {e}")
            return False

    def supprimer_machine(self, id_machine):
        try:
            cur = self._cursor()
            cur.execute("DELETE FROM machine_camera_association WHERE id_machine=%s", (id_machine,))
            cur.execute("DELETE FROM evenement WHERE id_machine=%s", (id_machine,))
            cur.execute("DELETE FROM alerte WHERE id_machine=%s", (id_machine,))
            cur.execute("DELETE FROM machine WHERE id_machine=%s", (id_machine,))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[MACHINE] supprimer_machine({id_machine}) : {e}")
            return False

    def get_emplacements(self):
        try:
            cur = self._cursor()
            cur.execute("SELECT id_emplacement, section_emplacement FROM emplacement ORDER BY id_emplacement")
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[MACHINE] get_emplacements : {e}")
            return []

    def get_machines_aruco_par_camera(self, id_camera):
        """
        Retourne un dict {aruco_id: id_machine} pour toutes les machines
        associées à cette caméra qui ont un aruco_id défini.
        """
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.id_machine, m.aruco_id
                FROM machine_camera_association mca
                JOIN machine m ON mca.id_machine = m.id_machine
                WHERE mca.id_camera = %s
                  AND m.aruco_id IS NOT NULL
            """, (id_camera,))
            rows = cur.fetchall()
            cur.close()
            # {aruco_id: id_machine}
            return {row['aruco_id']: row['id_machine'] for row in rows}
        except Exception as e:
            print(f"[MACHINE] get_machines_aruco_par_camera({id_camera}) : {e}")
            return {}

    def get_cameras_de_machine(self, id_machine):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT c.id_camera, c.nom_camera, c.ip_camera, c.protocole_camera
                FROM machine_camera_association mca
                JOIN camera c ON mca.id_camera = c.id_camera
                WHERE mca.id_machine = %s
            """, (id_machine,))
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[MACHINE] get_cameras_de_machine({id_machine}) : {e}")
            return []
