# coding: utf-8
from modele.supervision_base import _Base

class SupervisionCamera(_Base):

    def get_all_cameras(self):
        try:
            cur = self._cursor()
            cur.execute("SELECT id_camera, nom_camera, ip_camera, protocole_camera FROM camera ORDER BY id_camera")
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[CAMERA] get_all_cameras : {e}")
            return []

    def get_camera(self, id_camera):
        try:
            cur = self._cursor()
            cur.execute("SELECT * FROM camera WHERE id_camera = %s", (id_camera,))
            res = cur.fetchone()
            cur.close()
            return res
        except Exception as e:
            print(f"[CAMERA] get_camera : {e}")
            return None

    def ajouter_camera(self, nom, ip, protocole):
        try:
            cur = self._cursor()
            cur.execute("INSERT INTO camera (nom_camera, ip_camera, protocole_camera) VALUES (%s, %s, %s)", (nom, ip, protocole))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[CAMERA] ajouter_camera : {e}")
            return False

    def modifier_camera(self, id_camera, nom, ip, protocole):
        try:
            cur = self._cursor()
            cur.execute(
                "UPDATE camera SET nom_camera=%s, ip_camera=%s, protocole_camera=%s WHERE id_camera=%s",
                (nom, ip, protocole, id_camera)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[CAMERA] modifier_camera : {e}")
            return False

    def supprimer_camera(self, id_camera):
        try:
            cur = self._cursor()
            cur.execute("DELETE FROM machine_camera_association WHERE id_camera = %s", (id_camera,))
            cur.execute("DELETE FROM camera WHERE id_camera = %s", (id_camera,))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[CAMERA] supprimer_camera : {e}")
            return False
