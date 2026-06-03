# coding: utf-8
import requests
from flask import jsonify, request
from logger import get_logger

log = get_logger('CAM_CTRL')


class ControleurCameraCtrl:

    def __init__(self, appli):
        self.mysql  = appli.mysql
        self.config = appli.app.config

    def _reolink_post(self, ip, pwd, payload):
        url = f"http://{ip}/api.cgi?user=admin&password={pwd}"
        try:
            r = requests.post(url, json=payload, timeout=3)
            return r.json()
        except Exception as e:
            log.error(f"Reolink API erreur ({ip}) : {e}")
            return None

    def _get_cam_ip(self, id_camera):
        from modele.Supervision import Supervision
        model  = Supervision(self.mysql)
        camera = model.get_camera(id_camera)
        if not camera:
            return None, None
        ip = camera['ip_camera']
        if ip.startswith('rtsp://'):
            try:
                ip = ip.split('@')[1].split(':')[0]
            except Exception:
                return None, None
        pwd = self.config.get('DEFAULT_RTSP_PASS', '')
        return ip, pwd

    # ── PTZ ───────────────────────────────────────────────────────

    def api_ptz(self, id_camera):
        data  = request.get_json(silent=True) or {}
        op    = data.get('op', 'Stop')
        speed = data.get('speed', 10)
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False, "message": "Caméra introuvable"}), 404
        payload = [{"cmd": "PtzCtrl", "action": 0, "param": {
            "channel": 0, "op": op, "speed": speed
        }}]
        res = self._reolink_post(ip, pwd, payload)
        ok  = res and res[0].get('code') == 0
        log.info(f"PTZ cam {id_camera} → {op} (ok={ok})")
        return jsonify({"success": ok})

    # ── IR (mode nuit) ────────────────────────────────────────────

    def api_ir(self, id_camera):
        data  = request.get_json(silent=True) or {}
        state = data.get('state', 'Auto')
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        payload = [{"cmd": "SetIrLights", "action": 0, "param": {
            "IrLights": {"channel": 0, "state": state}
        }}]
        res = self._reolink_post(ip, pwd, payload)
        ok  = res and res[0].get('code') == 0
        log.info(f"IR cam {id_camera} → {state} (ok={ok})")
        return jsonify({"success": ok})

    def api_ir_get(self, id_camera):
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        url = f"http://{ip}/api.cgi?cmd=GetIrLights&user=admin&password={pwd}"
        try:
            res   = requests.get(url, timeout=3).json()
            state = res[0]['value']['IrLights']['state']
            return jsonify({"success": True, "state": state})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ── FloodLight (vrai flash) ───────────────────────────────────

    def api_led(self, id_camera):
        data  = request.get_json(silent=True) or {}
        state = 1 if data.get('state') == 'On' else 0
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        # Essai FloodLight d'abord, fallback PowerLed
        payload = [{"cmd": "SetWhiteLed", "action": 0, "param": {
            "WhiteLed": {"channel": 0, "state": state, "bright": 100}
        }}]
        res = self._reolink_post(ip, pwd, payload)
        if not res or res[0].get('code') != 0:
            # Fallback PowerLed
            payload2 = [{"cmd": "SetPowerLed", "action": 0, "param": {
                "PowerLed": {"channel": 0, "state": "On" if state else "Off"}
            }}]
            res = self._reolink_post(ip, pwd, payload2)
        ok = res and res[0].get('code') == 0
        log.info(f"LED cam {id_camera} → {'On' if state else 'Off'} (ok={ok})")
        return jsonify({"success": ok})

    def api_led_get(self, id_camera):
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        url = f"http://{ip}/api.cgi?cmd=GetWhiteLed&user=admin&password={pwd}"
        try:
            res   = requests.get(url, timeout=3).json()
            if res[0].get('code') == 0:
                state = res[0]['value']['WhiteLed']['state']
                return jsonify({"success": True, "state": "On" if state == 1 else "Off"})
        except Exception:
            pass
        # Fallback PowerLed
        try:
            url2  = f"http://{ip}/api.cgi?cmd=GetPowerLed&user=admin&password={pwd}"
            res2  = requests.get(url2, timeout=3).json()
            state = res2[0]['value']['PowerLed']['state']
            return jsonify({"success": True, "state": state})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ── Snap (capture photo) ──────────────────────────────────────

    def api_snap(self, id_camera):
        from flask import Response
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        try:
            r = requests.get(
                f"http://{ip}/cgi-bin/api.cgi?cmd=Snap&channel=0&user=admin&password={pwd}",
                timeout=5, stream=True
            )
            if r.headers.get('Content-Type', '').startswith('image'):
                return Response(r.content, mimetype='image/jpeg',
                    headers={"Content-Disposition": f"attachment; filename=snap_cam{id_camera}.jpg"})
            return jsonify({"success": False, "message": "Pas d'image"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ── Paramètres image ──────────────────────────────────────────

    def api_image_get(self, id_camera):
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        try:
            res = requests.get(f"http://{ip}/api.cgi?cmd=GetImage&user=admin&password={pwd}", timeout=3).json()
            if res[0].get('code') == 0:
                return jsonify({"success": True, "image": res[0]['value']['Image']})
            return jsonify({"success": False})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    def api_image_set(self, id_camera):
        data = request.get_json(silent=True) or {}
        ip, pwd = self._get_cam_ip(id_camera)
        if not ip:
            return jsonify({"success": False}), 404
        payload = [{"cmd": "SetImage", "action": 0, "param": {"Image": {
            "channel":    0,
            "bright":     data.get('bright', 128),
            "contrast":   data.get('contrast', 128),
            "saturation": data.get('saturation', 128),
            "sharpness":  data.get('sharpness', 128),
        }}}]
        res = self._reolink_post(ip, pwd, payload)
        ok  = res and res[0].get('code') == 0
        return jsonify({"success": ok})