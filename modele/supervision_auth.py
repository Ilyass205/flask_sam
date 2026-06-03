# coding: utf-8
from modele.supervision_base import _Base
from werkzeug.security import generate_password_hash, check_password_hash

# Rôles et leurs permissions
PERMISSIONS = {
    'admin':       ['tout'],
    'technicien':  ['voir_cams', 'changer_etat', 'voir_rapports'],
    'superviseur': ['voir_cams', 'voir_rapports'],
}

def a_permission(role: str, perm: str) -> bool:
    perms = PERMISSIONS.get(role, [])
    return 'tout' in perms or perm in perms


class SupervisionAuth(_Base):

    def test_login(self, login, mdp):
        try:
            cur = self._cursor()
            cur.execute(
                "SELECT id_user, login_user, role_user, mdph_user FROM user "
                "WHERE login_user = %s",
                (login,)
            )
            res = cur.fetchone()
            cur.close()
            if res is None:
                return None
            # Vérifie le mot de passe : supporte l'ancien format clair ET le nouveau hashé
            mdp_bdd = res['mdph_user']
            if mdp_bdd.startswith('pbkdf2:') or mdp_bdd.startswith('scrypt:'):
                ok = check_password_hash(mdp_bdd, mdp)
            else:
                # Ancien compte en clair — on accepte mais on logue un avertissement
                import logging
                logging.getLogger('AUTH').warning(
                    f"Compte '{login}' utilise un mot de passe non hashé — migrer via /api/users"
                )
                ok = (mdp_bdd == mdp)
            if not ok:
                return None
            return {'id_user': res['id_user'], 'login_user': res['login_user'], 'role_user': res['role_user']}
        except Exception as e:
            print(f"[AUTH] ERREUR BDD : {e}")
            # CORRECTION : suppression de la backdoor admin/sam2026
            return None

    def get_users(self):
        try:
            cur = self._cursor()
            cur.execute("SELECT id_user, login_user, role_user FROM user ORDER BY id_user")
            res = cur.fetchall()
            cur.close()
            return res
        except Exception as e:
            print(f"[AUTH] get_users : {e}")
            return []

    def ajouter_user(self, login, mdp, role):
        try:
            cur = self._cursor()
            mdp_hash = generate_password_hash(mdp)
            cur.execute(
                "INSERT INTO user (login_user, mdph_user, role_user) VALUES (%s, %s, %s)",
                (login, mdp_hash, role)
            )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[AUTH] ajouter_user : {e}")
            return False

    def modifier_user(self, id_user, login, role, mdp=None):
        try:
            cur = self._cursor()
            if mdp:
                mdp_hash = generate_password_hash(mdp)
                cur.execute(
                    "UPDATE user SET login_user=%s, role_user=%s, mdph_user=%s WHERE id_user=%s",
                    (login, role, mdp_hash, id_user)
                )
            else:
                cur.execute(
                    "UPDATE user SET login_user=%s, role_user=%s WHERE id_user=%s",
                    (login, role, id_user)
                )
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[AUTH] modifier_user : {e}")
            return False

    def supprimer_user(self, id_user):
        try:
            cur = self._cursor()
            cur.execute("DELETE FROM user WHERE id_user=%s", (id_user,))
            self._commit()
            cur.close()
            return True
        except Exception as e:
            print(f"[AUTH] supprimer_user : {e}")
            return False