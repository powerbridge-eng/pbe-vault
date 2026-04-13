import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time, json, base64
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string, render_template, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from io import BytesIO

# --- 1. CORE CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ADMIN_PASSWORD = "PBE-Global-2026"
SUPERVISOR_PASSWORD = "PBE_Secure_2026"

app = Flask(__name__)
app.secret_key = "PBE_ABSOLUTE_SOVEREIGN_BUILD_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    for i in range(5):
        try: return psycopg2.connect(DATABASE_URL)
        except: time.sleep(2)
    return None

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_registry_2026 (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            gender TEXT, nationality TEXT, pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, 
            rank TEXT, department TEXT, phone_no TEXT, email TEXT, ghana_card_no TEXT, 
            photo_url TEXT, ghana_card_url TEXT, status TEXT DEFAULT 'PENDING', 
            otp_code TEXT, region TEXT, station TEXT, issuance_date DATE, expiry_date DATE,
            visual_blueprint TEXT DEFAULT '{}'
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_audit_2026 (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, actor TEXT, details TEXT, ip_address TEXT, device_info TEXT);")
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_db()

# --- 2. COMMAND LOGIC (LIFE INJECTION) ---

@app.route("/admin/visual-editor/<uid>")
def visual_editor(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    return render_template('editor.html', uid=uid, w=w)

@app.route("/admin/review/<uid>")
def review_cmd(uid):
    if not session.get('role'): abort(403)
    # This renders the detailed dossier view for approval
    return f"Reviewing Dossier for {uid}. AI Analysis in progress..."

@app.route("/admin/promote/<uid>")
def promote_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE pbe_registry_2026 SET rank = 'Senior Master Technician' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/suspend/<uid>")
def suspend_cmd(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE pbe_registry_2026 SET status = 'SUSPENDED' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/unsuspend/<uid>")
def unsuspend_cmd(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete/<uid>")
def delete_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

# --- 3. EXECUTIVE UI & DASHBOARD ---

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Supreme Command Center</title>
    <style>
        :root { --navy: #2c3e50; --gold: #ffc107; --bg: #f4f7f6; --dark: #34495e; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 50px; }
        .header { background: var(--dark); color: white; padding: 30px; text-align: center; border-bottom: 5px solid var(--gold); }
        .logo-circle { width: 70px; height: 70px; background: #fff; border-radius: 50%; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; border: 3px solid var(--gold); overflow: hidden; }
        .logo-circle img { width: 90%; height: auto; }
        .container { max-width: 1400px; margin: auto; padding: 20px; }
        .search-container { display: flex; gap: 10px; margin-bottom: 30px; }
        .search-bar { flex: 1; padding: 15px; border-radius: 8px; border: 1px solid #ddd; outline: none; }
        .section-card { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .section-title { font-size: 13px; font-weight: 800; color: #7f8c8d; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
        .matrix-item { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 15px; font-size: 11px; font-weight: bold; display: flex; justify-content: space-between; }
        .registry-table { width: 100%; border-collapse: collapse; }
        .registry-table th { text-align: left; padding: 15px; border-bottom: 2px solid #eee; font-size: 12px; color: #95a5a6; }
        .registry-table td { padding: 15px; border-bottom: 1px solid #f9f9f9; font-size: 13px; }
        .btn-suite { padding: 8px 12px; border-radius: 5px; color: white; text-decoration: none; font-size: 10px; font-weight: bold; margin-right: 4px; display: inline-block; border: none; cursor: pointer; }
        .bg-print { background: #3498db; } .bg-dossier { background: #34495e; } .bg-email { background: #7f8c8d; } .bg-wa { background: #27ae60; } .bg-promote { background: #f1c40f; color: #000; } .bg-sus { background: #95a5a6; } .bg-unsus { background: #2980b9; } .bg-del { background: #e74c3c; }
        .bg-cloudinary { background: #34495e; color: white; font-weight: bold; padding: 15px; border-radius: 8px; }
        .fab-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; }
        .fab { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; text-decoration: none; box-shadow: 0 10px 20px rgba(0,0,0,0.2); font-size: 20px; }
        .fab-alert { background: #f1c40f; color: #000; } .fab-audit { background: #34495e; } .fab-add { background: #e67e22; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-circle">
            <img src="{{ url_for('static', filename='logo.png') }}" onerror="this.src='https://res.cloudinary.com/pbe-engineering/image/upload/v1/logo_pbe.png'">
        </div>
        <div style="font-size: 26px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
        <div style="font-size: 11px; color: var(--gold); margin-top: 5px;">OPERATOR: {{ session.get('op_name', 'SYSTEM') }}</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
    
    <div class="fab-container">
        <a href="/admin/alerts" class="fab fab-alert" title="Alerts">🔔 0</a>
        <a href="/admin/audit" class="fab fab-audit" title="Audit Log">📜</a>
        <a href="/admin/invite" class="fab fab-add" title="Add Personnel">＋</a>
    </div>
</body>
</html>
"""

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall()
    
    # Static Simulation of your provided metrics
    GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]
    PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "GENERAL TECHNICAL"]
    
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="search-container">
            <input type="text" class="search-bar" placeholder="Search Master Registry...">
            <a href="https://cloudinary.com/console" target="_blank" class="bg-cloudinary">☁️ CLOUDINARY</a>
            <div style="padding:15px; border-radius:8px; background:#fff; border:1px solid #ddd; font-weight:bold;">SMS: <span style="color:#27ae60;">OFFLINE</span></div>
        </div>

        <div class="section-card">
            <div class="section-title">🌍 16-REGION GLOBAL METRIC</div>
            <div class="matrix-grid">
                {% for reg in regions %}
                <div class="matrix-item"><span>{{reg}}:</span> <b style="color:#e74c3c;">{{ 1 if reg == 'Greater Accra' else 0 }}</b></div>
                {% endfor %}
            </div>
        </div>

        <div class="section-card">
            <div class="section-title">🛠️ TECHNICAL GUILDS WORKFORCE METRIC</div>
            <div class="matrix-grid">
                {% for guild in guilds %}
                <div class="matrix-item"><span>{{guild}}</span> <b style="color:#e74c3c;">{{ 1 if guild == 'ELECTRICAL ENGINEERING' else 0 }}</b></div>
                {% endfor %}
            </div>
        </div>

        <div class="section-card">
            <div class="section-title">👤 PERSONNEL REGISTRY CONTROL</div>
            <div style="overflow-x:auto;">
                <table class="registry-table">
                    <thead><tr><th>PBE-ID / LICENSE</th><th>NAME</th><th>RANK & DEPT</th><th>STATUS</th><th>COMMAND SUITE</th></tr></thead>
                    <tbody>
                        {% for w in workers %}
                        <tr>
                            <td>ID: <b>{{ w[6] }}</b><br><small>{{ w[7] }}</small></td>
                            <td>{{ w[1] }}, {{ w[2] }}</td>
                            <td><b style="color:#e74c3c;">{{ w[8] }}</b><br><small>{{ w[9] }}</small></td>
                            <td><b style="color:#27ae60;">{{ w[15] }}</b></td>
                            <td>
                                <a href="/admin/visual-editor/{{ w[6] }}" class="btn-suite bg-print">PRINT</a>
                                <a href="/admin/review/{{ w[6] }}" class="btn-suite bg-dossier">REVIEW DOSSIER</a>
                                <a href="mailto:{{ w[11] }}" class="btn-suite bg-email">EMAIL</a>
                                <a href="https://wa.me/{{ w[10] }}" class="btn-suite bg-wa">WA</a>
                                <a href="/admin/promote/{{ w[6] }}" class="btn-suite bg-promote">PROMOTE</a>
                                <a href="/admin/suspend/{{ w[6] }}" class="btn-suite bg-sus">SUSPEND</a>
                                <a href="/admin/unsuspend/{{ w[6] }}" class="btn-suite bg-unsus">UNSUSPEND</a>
                                <a href="/admin/delete/{{ w[6] }}" class="btn-suite bg-del" onclick="return confirm('Erase Soul Record?')">DELETE</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    """), regions=GHANA_REGIONS, guilds=PBE_GUILDS, workers=workers)

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'], session['op_name'] = 'ADMIN', request.form.get('op_name', 'GENERAL IMPERIAL')
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div style="text-align:center; padding:100px;"><h3>HQ SYSTEM LOCK</h3><form method="POST"><input name="op_name" placeholder="Operator Name" required><br><br><input type="password" name="password" placeholder="Key" required><br><br><button class="bg-cloudinary" style="border:none; cursor:pointer; width:200px;">UNLOCK</button></form></div>'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
