# coding: utf-8
import io
import csv
import datetime
from modele.supervision_base import _Base


class SupervisionRapport(_Base):

    def get_donnees_rapport(self):
        return {
            "evenements": self._get_evenements(),
            "etats":      self._get_etats_actuels(),
            "alertes":    self._get_alertes_rapport(),
            "genere_le":  datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

    def _get_evenements(self):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT ev.id_evenement, ev.horodatage_evenement,
                       m.nom_machine, m.type_machine, e.section_emplacement,
                       c.nom_couleur, c.etat_couleur
                FROM evenement ev
                JOIN machine m  ON ev.id_machine = m.id_machine
                JOIN couleur c  ON ev.id_couleur = c.id_couleur
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                ORDER BY ev.horodatage_evenement DESC
                LIMIT 500
            """)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        except Exception as ex:
            print(f"[RAPPORT] _get_evenements : {ex}")
            return []

    def _get_etats_actuels(self):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT m.id_machine, m.nom_machine, m.type_machine,
                       e.section_emplacement,
                       c.nom_couleur, c.etat_couleur,
                       ev.horodatage_evenement
                FROM machine m
                LEFT JOIN emplacement e ON m.id_emplacement = e.id_emplacement
                LEFT JOIN evenement ev ON ev.id_evenement = (
                    SELECT id_evenement FROM evenement
                    WHERE id_machine = m.id_machine
                    ORDER BY horodatage_evenement DESC LIMIT 1
                )
                LEFT JOIN couleur c ON ev.id_couleur = c.id_couleur
                ORDER BY m.id_machine
            """)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        except Exception as ex:
            print(f"[RAPPORT] _get_etats_actuels : {ex}")
            return []

    def _get_alertes_rapport(self):
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT a.id_alerte, a.date_alerte, a.type_alerte,
                       m.nom_machine, m.type_machine
                FROM alerte a
                JOIN machine m ON a.id_machine = m.id_machine
                ORDER BY a.date_alerte DESC
            """)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
        except Exception as ex:
            print(f"[RAPPORT] _get_alertes_rapport : {ex}")
            return []


def _fmt(val):
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y %H:%M:%S")
    return val or ""


def generer_csv_evenements(evenements):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(["ID", "Horodatage", "Machine", "Type", "Emplacement", "Couleur", "État"])
    for ev in evenements:
        w.writerow([ev.get("id_evenement",""), _fmt(ev.get("horodatage_evenement")),
                    ev.get("nom_machine",""), ev.get("type_machine",""),
                    ev.get("section_emplacement",""), ev.get("nom_couleur",""), ev.get("etat_couleur","")])
    return buf.getvalue().encode("utf-8-sig")


def generer_csv_etats(etats):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(["Machine", "Type", "Emplacement", "État actuel", "Couleur", "Depuis le"])
    for et in etats:
        w.writerow([et.get("nom_machine",""), et.get("type_machine",""),
                    et.get("section_emplacement",""), et.get("etat_couleur") or "inconnu",
                    et.get("nom_couleur") or "—", _fmt(et.get("horodatage_evenement"))])
    return buf.getvalue().encode("utf-8-sig")


def generer_csv_alertes(alertes):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(["ID", "Date", "Type d'alerte", "Machine", "Type machine"])
    for al in alertes:
        w.writerow([al.get("id_alerte",""), _fmt(al.get("date_alerte")),
                    al.get("type_alerte",""), al.get("nom_machine",""), al.get("type_machine","")])
    return buf.getvalue().encode("utf-8-sig")


def generer_csv_complet(data):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow([f"Rapport généré le : {data['genere_le']}"])
    w.writerow([])
    w.writerow(["=== ÉTAT ACTUEL DES MACHINES ==="])
    buf.write(generer_csv_etats(data["etats"]).decode("utf-8-sig").lstrip("\ufeff"))
    w.writerow([])
    w.writerow(["=== HISTORIQUE DES ÉVÉNEMENTS ==="])
    buf.write(generer_csv_evenements(data["evenements"]).decode("utf-8-sig").lstrip("\ufeff"))
    w.writerow([])
    w.writerow(["=== ALERTES ==="])
    buf.write(generer_csv_alertes(data["alertes"]).decode("utf-8-sig").lstrip("\ufeff"))
    return buf.getvalue().encode("utf-8-sig")


def _badge_couleur(etat):
    colors = {
        "marche":      ("#1B8A4C", "#e6f4ec"),
        "arret":       ("#C62828", "#fdecea"),
        "maintenance": ("#E65100", "#fff3e0"),
    }
    return colors.get(etat, ("#555", "#eee"))


def generer_html_rapport(data):
    now = data["genere_le"]

    # Calcul stats pour le rapport
    etats       = data["etats"]
    evenements  = data["evenements"]
    alertes     = data["alertes"]
    nb_machines = len(etats)
    nb_marche   = sum(1 for e in etats if e.get("etat_couleur") == "marche")
    nb_arret    = sum(1 for e in etats if e.get("etat_couleur") == "arret")
    nb_maint    = sum(1 for e in etats if e.get("etat_couleur") == "maintenance")
    trs         = round(nb_marche / nb_machines * 100) if nb_machines > 0 else 0

    css = """<style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',Arial,sans-serif;font-size:12px;color:#1a1d23;background:#fff;padding:32px}
    .header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:32px;padding-bottom:20px;border-bottom:2px solid #1565C0;}
    .header-left h1{font-size:24px;font-weight:700;color:#1565C0;}
    .header-left p{font-size:11px;color:#888;margin-top:4px;}
    .header-right{text-align:right;font-size:11px;color:#888;}
    .kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px;}
    .kpi{background:#f7f8fa;border-radius:8px;padding:14px;text-align:center;}
    .kpi-val{font-size:28px;font-weight:700;color:#1565C0;}
    .kpi-label{font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-top:4px;}
    h2{font-size:14px;font-weight:700;color:#333;margin:28px 0 10px;border-left:4px solid #1565C0;padding-left:10px;}
    table{width:100%;border-collapse:collapse;margin-bottom:8px;}
    th{background:#1565C0;color:#fff;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;}
    td{padding:7px 12px;border-bottom:1px solid #e8eaf0;font-size:11.5px;}
    tr:nth-child(even) td{background:#f7f8fa}
    .badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:700;}
    .footer{margin-top:40px;font-size:10px;color:#aaa;text-align:center;border-top:1px solid #eee;padding-top:12px;}
    @media print{body{padding:16px}}
    </style>"""

    html = f'<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Rapport – JOGAM SAMv2</title>{css}</head><body>'

    # En-tête
    html += f"""<div class="header">
        <div class="header-left">
            <h1>📊 Rapport de supervision atelier</h1>
            <p>Système de supervision JOGAM SAMv2 — Rapport automatique</p>
        </div>
        <div class="header-right">
            Généré le {now}<br>
            <strong>{nb_machines} machines</strong> supervisées
        </div>
    </div>"""

    # KPIs
    html += f"""<div class="kpi-grid">
        <div class="kpi"><div class="kpi-val">{nb_machines}</div><div class="kpi-label">Machines</div></div>
        <div class="kpi"><div class="kpi-val" style="color:#1B8A4C">{nb_marche}</div><div class="kpi-label">En marche</div></div>
        <div class="kpi"><div class="kpi-val" style="color:#C62828">{nb_arret}</div><div class="kpi-label">À l'arrêt</div></div>
        <div class="kpi"><div class="kpi-val">{trs}%</div><div class="kpi-label">TRS Global</div></div>
    </div>"""

    # État des machines
    html += "<h2>État actuel des machines</h2><table>"
    html += "<tr><th>Machine</th><th>Type</th><th>Emplacement</th><th>État</th><th>Depuis</th></tr>"
    for et in etats:
        etat = et.get("etat_couleur") or "inconnu"
        fg, bg = _badge_couleur(etat)
        badge = f'<span class="badge" style="color:{fg};background:{bg}">{et.get("nom_couleur") or "—"}</span>'
        html += f'<tr><td><strong>{et.get("nom_machine","")}</strong></td><td>{et.get("type_machine","")}</td><td>{et.get("section_emplacement") or "—"}</td><td>{badge}</td><td>{_fmt(et.get("horodatage_evenement"))}</td></tr>'
    html += "</table>"

    # Historique événements
    html += f"<h2>Historique des événements <span style='font-weight:400;font-size:11px;color:#888'>({len(evenements)} derniers)</span></h2><table>"
    html += "<tr><th>Horodatage</th><th>Machine</th><th>Emplacement</th><th>État</th></tr>"
    for ev in evenements[:50]:
        etat = ev.get("etat_couleur") or "inconnu"
        fg, bg = _badge_couleur(etat)
        badge = f'<span class="badge" style="color:{fg};background:{bg}">{ev.get("nom_couleur") or "—"}</span>'
        html += f'<tr><td style="font-family:monospace">{_fmt(ev.get("horodatage_evenement"))}</td><td>{ev.get("nom_machine","")}</td><td>{ev.get("section_emplacement") or "—"}</td><td>{badge}</td></tr>'
    if len(evenements) > 50:
        html += f'<tr><td colspan="4" style="text-align:center;color:#888;font-style:italic;">... et {len(evenements)-50} événements supplémentaires dans le CSV complet</td></tr>'
    html += "</table>"

    # Alertes
    html += f"<h2>Alertes <span style='font-weight:400;font-size:11px;color:#888'>({len(alertes)} au total)</span></h2>"
    if alertes:
        html += "<table><tr><th>Date</th><th>Type</th><th>Machine</th></tr>"
        for al in alertes:
            html += f'<tr><td style="font-family:monospace">{_fmt(al.get("date_alerte"))}</td><td>{al.get("type_alerte","")}</td><td>{al.get("nom_machine","")}</td></tr>'
        html += "</table>"
    else:
        html += "<p style='color:#888;font-style:italic;margin:10px 0;'>Aucune alerte enregistrée.</p>"

    html += f'<div class="footer">Rapport généré automatiquement — JOGAM Supervision Atelier — {now}</div>'
    html += '</body></html>'
    return html


def generer_pdf_rapport(data):
    html_content = generer_html_rapport(data)
    try:
        from weasyprint import HTML
        return HTML(string=html_content).write_pdf(), "application/pdf", ".pdf"
    except ImportError:
        return html_content.encode("utf-8"), "text/html", ".html"
