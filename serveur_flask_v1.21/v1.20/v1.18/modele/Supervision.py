# coding: utf-8
from modele.supervision_base        import _Base
from modele.supervision_auth        import SupervisionAuth
from modele.supervision_camera      import SupervisionCamera
from modele.supervision_machine     import SupervisionMachine
from modele.supervision_association import SupervisionAssociation
from modele.supervision_evenement   import SupervisionEvenement
from modele.supervision_alerte      import SupervisionAlerte
from modele.supervision_rapport     import SupervisionRapport
from modele.supervision_stats       import SupervisionStats


class Supervision(
    SupervisionAuth,
    SupervisionCamera,
    SupervisionMachine,
    SupervisionAssociation,
    SupervisionEvenement,
    SupervisionAlerte,
    SupervisionRapport,
    SupervisionStats,
):
    def __init__(self, mysql):
        _Base.__init__(self, mysql)
