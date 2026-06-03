# coding: utf-8
"""
modele/supervision_association.py

Gestion des associations caméra <-> machine.
"""
from modele.supervision_base import _Base


class SupervisionAssociation(_Base):

    def get_cameras_avec_machines(self):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT c.id_camera, c.nom_camera, c.ip_camera, c.protocole_camera,
                       m.id_machine, m.nom_machine, m.type_machine,
                       e.section_emplacement
                FROM camera c
                LEFT JOIN machine_camera_association mca ON c.id_camera = mca.id_camera
                LEFT JOIN machine m ON mca.id_machine = m.id_machine
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                ORDER BY c.id_camera, m.id_machine
            """)
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[ASSOC] get_cameras_avec_machines : {e}")
            return []

    def ajouter_association(self, id_camera, id_machine):
        try:
            cur = self._cursor()
            cur.execute(
                "INSERT INTO machine_camera_association (id_machine, id_camera) "
                "VALUES (%s, %s)",
                (id_machine, id_camera)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[ASSOC] ajouter_association : {e}")
            return False

    def supprimer_association(self, id_camera, id_machine):
        try:
            cur = self._cursor()
            cur.execute(
                "DELETE FROM machine_camera_association "
                "WHERE id_camera = %s AND id_machine = %s",
                (id_camera, id_machine)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[ASSOC] supprimer_association : {e}")
            return False
