# coding: utf-8
from flask import Flask
from flask_mysqldb import MySQL
from datetime import timedelta
from modele.camera_manager import CameraManager
from modele.detecteur_couleur import DetecteurCouleur
import config


class Application:

    def __init__(self):
        self.app = Flask(__name__, template_folder='./templates', static_folder='./static')
        self.app.config.update(config.FLASK_CONFIG)
        self.app.permanent_session_lifetime = timedelta(seconds=config.PERMANENT_SESSION_LIFETIME)
        self.mysql     = MySQL()
        self.mysql.init_app(self.app)
        self.cam_mgr   = CameraManager()
        self.detecteur = DetecteurCouleur(self.cam_mgr, api_base_url=config.API_BASE_URL)
        from controleur import ControleurPrincipal
        self.cp = ControleurPrincipal(self)
        self._routage()

    def _routage(self):
        cp  = self.cp
        app = self.app

        publiques = [
            'afficher_login', 'traiter_login', 'static',
            'erreur_404', 'erreur_500', 'video_feed', 'api_inserer_evenement',
            'test_yolo', 'test_yolo_feed'
        ]

        @app.before_request
        def before_request():
            return cp.test_before_request(publiques)

        app.register_error_handler(404, cp.erreur_404)
        app.register_error_handler(500, cp.erreur_500)

        # ── Auth ─────────────────────────────────────────────────
        app.add_url_rule('/',            'afficher_login', cp.afficher_login,  methods=['GET'])
        app.add_url_rule('/test_login',  'traiter_login',  cp.traiter_login,   methods=['POST'])
        app.add_url_rule('/deconnexion', 'deconnexion',    cp.deconnexion,     methods=['GET'])
        app.add_url_rule('/deconnexionb','deconnexionb',   cp.deconnexionb,    methods=['GET'])

        # ── Pages principales ─────────────────────────────────────
        app.add_url_rule('/index',                  'index',           cp.afficher_index,   methods=['GET'])
        app.add_url_rule('/camera/<int:id_camera>', 'view_camera',     cp.afficher_camera,  methods=['GET'])
        app.add_url_rule('/cameras_direct',         'cameras_direct',  cp.cameras_direct,   methods=['GET'])
        app.add_url_rule('/historique',             'historique',      cp.historique,       methods=['GET'])
        app.add_url_rule('/alertes',                'alertes',         cp.alertes,          methods=['GET'])
        app.add_url_rule('/machines_config',        'machines_config', cp.machines_config,  methods=['GET'])
        app.add_url_rule('/rapports',               'rapports',        cp.rapports,         methods=['GET'])
        app.add_url_rule('/stats',                  'stats',           cp.afficher_stats,   methods=['GET'])
        app.add_url_rule('/users',                  'users',           cp.afficher_users,   methods=['GET'])

        # ── Streaming ────────────────────────────────────────────
        app.add_url_rule('/video_feed/<int:id_camera>', 'video_feed', cp.video_feed, methods=['GET'])

        # ── API Caméras ───────────────────────────────────────────
        app.add_url_rule('/api/cameras',                 'api_get_cameras',      cp.api_get_cameras,      methods=['GET'])
        app.add_url_rule('/api/cameras',                 'api_ajouter_camera',   cp.api_ajouter_camera,   methods=['POST'])
        app.add_url_rule('/api/cameras/<int:id_camera>', 'api_modifier_camera',  cp.api_modifier_camera,  methods=['PUT'])
        app.add_url_rule('/api/cameras/<int:id_camera>', 'api_supprimer_camera', cp.api_supprimer_camera, methods=['DELETE'])

        # ── API Contrôle caméra ───────────────────────────────────
        app.add_url_rule('/api/cameras/<int:id_camera>/ptz', 'api_ptz',     cp.api_ptz,     methods=['POST'])
        app.add_url_rule('/api/cameras/<int:id_camera>/ir',  'api_ir',      cp.api_ir,      methods=['POST'])
        app.add_url_rule('/api/cameras/<int:id_camera>/ir',  'api_ir_get',  cp.api_ir_get,  methods=['GET'])
        app.add_url_rule('/api/cameras/<int:id_camera>/led', 'api_led',     cp.api_led,     methods=['POST'])
        app.add_url_rule('/api/cameras/<int:id_camera>/led', 'api_led_get', cp.api_led_get, methods=['GET'])
        app.add_url_rule('/api/cameras/<int:id_camera>/snap','api_snap',    cp.api_snap,    methods=['GET'])
        app.add_url_rule('/api/cameras/<int:id_camera>/image','api_image_get', cp.api_image_get, methods=['GET'])
        app.add_url_rule('/api/cameras/<int:id_camera>/image','api_image_set', cp.api_image_set, methods=['POST'])

        # ── API Machines ──────────────────────────────────────────
        app.add_url_rule('/api/machines',                  'api_get_machines',     cp.api_get_machines,     methods=['GET'])
        app.add_url_rule('/api/machines',                  'api_ajouter_machine',  cp.api_ajouter_machine,  methods=['POST'])
        app.add_url_rule('/api/machines/<int:id_machine>', 'api_modifier_machine', cp.api_modifier_machine, methods=['PUT'])
        app.add_url_rule('/api/machines/<int:id_machine>', 'api_supprimer_machine',cp.api_supprimer_machine,methods=['DELETE'])
        app.add_url_rule('/api/emplacements',              'api_get_emplacements', cp.api_get_emplacements, methods=['GET'])

        # ── API Associations ──────────────────────────────────────
        app.add_url_rule('/api/associations',                                  'api_ajouter_association',  cp.api_ajouter_association,  methods=['POST'])
        app.add_url_rule('/api/associations/<int:id_camera>/<int:id_machine>', 'api_supprimer_association',cp.api_supprimer_association, methods=['DELETE'])

        # ── API Événements & Alertes ──────────────────────────────
        app.add_url_rule('/api/etat/<int:id_machine>',     'api_get_etat_machine',  cp.api_get_etat_machine,     methods=['GET'])
        app.add_url_rule('/api/historique/<int:id_machine>','api_get_historique',   cp.api_get_historique_machine,methods=['GET'])
        app.add_url_rule('/api/evenements',                'api_inserer_evenement', cp.api_inserer_evenement,    methods=['POST'])
        app.add_url_rule('/api/alertes',                   'api_get_alertes',       cp.api_get_alertes,          methods=['GET'])
        app.add_url_rule('/api/alertes/ajouter',           'api_ajouter_alerte',    cp.api_ajouter_alerte,       methods=['POST'])
        app.add_url_rule('/api/alertes/<int:id_alerte>',   'api_supprimer_alerte',  cp.api_supprimer_alerte,     methods=['DELETE'])
        app.add_url_rule('/api/machines/liste',            'api_get_machines_liste',cp.api_get_machines_pour_alerte, methods=['GET'])
        app.add_url_rule('/test_yolo',                     'test_yolo',             cp.test_yolo,                methods=['GET'])
        app.add_url_rule('/test_yolo_feed/<int:id_camera>','test_yolo_feed',        cp.test_yolo_feed,           methods=['GET'])

        # ── API Stats ─────────────────────────────────────────────
        app.add_url_rule('/api/stats/dashboard',  'api_stats_dashboard',  cp.api_stats_dashboard,  methods=['GET'])
        app.add_url_rule('/api/stats/etats',      'api_stats_etats',      cp.api_stats_etats,      methods=['GET'])
        app.add_url_rule('/api/stats/evenements', 'api_stats_evenements', cp.api_stats_evenements, methods=['GET'])
        app.add_url_rule('/api/stats/machines',   'api_stats_machines',   cp.api_stats_machines,   methods=['GET'])

        # ── API Users ─────────────────────────────────────────────
        app.add_url_rule('/api/users',              'api_get_users',     cp.api_get_users,     methods=['GET'])
        app.add_url_rule('/api/users',              'api_ajouter_user',  cp.api_ajouter_user,  methods=['POST'])
        app.add_url_rule('/api/users/<int:id_user>','api_modifier_user', cp.api_modifier_user, methods=['PUT'])
        app.add_url_rule('/api/users/<int:id_user>','api_supprimer_user',cp.api_supprimer_user,methods=['DELETE'])

        # ── Rapports ──────────────────────────────────────────────
        app.add_url_rule('/rapports/csv/complet',    'rapport_csv_complet',    cp.rapport_csv_complet,    methods=['GET'])
        app.add_url_rule('/rapports/csv/evenements', 'rapport_csv_evenements', cp.rapport_csv_evenements, methods=['GET'])
        app.add_url_rule('/rapports/csv/etats',      'rapport_csv_etats',      cp.rapport_csv_etats,      methods=['GET'])
        app.add_url_rule('/rapports/csv/alertes',    'rapport_csv_alertes',    cp.rapport_csv_alertes,    methods=['GET'])
        app.add_url_rule('/rapports/pdf',            'rapport_pdf',            cp.rapport_pdf,            methods=['GET'])
        app.add_url_rule('/rapports/apercu',         'rapport_apercu',         cp.rapport_apercu,         methods=['GET'])

    def run(self, host='0.0.0.0', port=5000):
        # CORRECTION : debug=False en production (était debug=True)
        self.app.run(host=host, port=port, debug=config.FLASK_DEBUG, use_reloader=False)