# coding: utf-8
from controleur.controleur_auth        import ControleurAuth
from controleur.controleur_camera      import ControleurCamera
from controleur.controleur_camera_ctrl import ControleurCameraCtrl
from controleur.controleur_machine     import ControleurMachine
from controleur.controleur_association import ControleurAssociation
from controleur.controleur_event       import ControleurEvent
from controleur.controleur_report      import ControleurReport
from controleur.controleur_erreurs     import ControleurErreurs
from controleur.controleur_stats       import ControleurStats


class ControleurPrincipal(
    ControleurAuth,
    ControleurCamera,
    ControleurCameraCtrl,
    ControleurMachine,
    ControleurAssociation,
    ControleurEvent,
    ControleurReport,
    ControleurErreurs,
    ControleurStats,
):
    def __init__(self, appli):
        ControleurAuth.__init__(self, appli)
        ControleurCamera.__init__(self, appli)
        ControleurCameraCtrl.__init__(self, appli)
        ControleurMachine.__init__(self, appli)
        ControleurAssociation.__init__(self, appli)
        ControleurEvent.__init__(self, appli)
        ControleurReport.__init__(self, appli)
        ControleurErreurs.__init__(self, appli)
        ControleurStats.__init__(self, appli)
