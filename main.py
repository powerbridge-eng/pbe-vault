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
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pbe_registry_2026' AND column_name='visual_blueprint';")
    if not cur.fetchone():
        cur.execute("ALTER TABLE pbe_registry_2026 ADD COLUMN visual_blueprint TEXT DEFAULT '{}';")
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
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_db()

# --- 2. PERMANENT VISUAL BRIDGE ---
@app.route("/admin/visual-editor/<uid>")
def visual_editor(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: abort(404)
    # The blueprint (w[21]) contains the Photoshop memory
    return render_template('editor.html', uid=uid, w=w, blueprint=w[21])

@app.route("/process-visual-print", methods=['POST'])
def process_visual_print():
    if not session.get('role'): abort(403)
    data = request.json
    img_data, uid = data.get('image').split(',')[1], data.get('uid')
    blueprint = json.dumps(data.get('blueprint')) 

    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE pbe_registry_2026 SET visual_blueprint = %s WHERE pbe_uid = %s", (blueprint, uid))
    conn.commit(); cur.close(); conn.close()

    session[f'print_ready_{uid}'] = img_data
    return jsonify({"status": "success", "redirect": url_for('download_final_pdf', uid=uid)})

@app.route("/download-final-pdf/<uid>")
def download_final_pdf(uid):
    img_data = session.get(f'print_ready_{uid}')
    if not img_data: return "Session Expired", 404
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    img_bytes = BytesIO(base64.b64decode(img_data))
    c.drawImage(ImageReader(img_bytes), 0, 0, width=3.375*inch, height=2.125*inch)
    c.showPage(); c.save(); buffer.seek(0)
    session.pop(f'print_ready_{uid}', None)
    return send_file(buffer, mimetype='application/pdf', download_name=f"PBE_ID_{uid}.pdf")

# --- 3. EXECUTIVE DASHBOARD (RESTORED TO SCREENSHOT STYLE) ---
PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "GENERAL TECHNICAL"]
GHANA_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command Center</title>
    <style>
        :root { --navy: #2c3e50; --gold: #ffc107; --bg: #f8f9fa; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding-bottom: 50px; }
        .header { background: #34495e; color: white; padding: 20px; text-align: center; border-bottom: 4px solid var(--gold); }
        .container { max-width: 1400px; margin: auto; padding: 20px; }
        .search-container { display: flex; gap: 10px; margin-bottom: 25px; align-items: center; }
        .search-bar { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #ddd; outline: none; font-size: 14px; }
        .metric-card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .metric-title { font-size: 12px; font-weight: 800; color: #7f8c8d; text-transform: uppercase; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
        .metric-item { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 12px; font-size: 11px; font-weight: 700; color: #2c3e50; display: flex; justify-content: space-between; align-items: center; }
        .registry-table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; }
        .registry-table th { background: #fdfdfd; text-align: left; padding: 15px; border-bottom: 2px solid #eee; font-size: 12px; color: #95a5a6; }
        .registry-table td { padding: 15px; border-bottom: 1px solid #f9f9f9; font-size: 13px; }
        .btn-suite { padding: 8px 14px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: 900; margin-right: 5px; display: inline-block; text-transform: uppercase; }
        .bg-print { background: #3498db; } .bg-wa { background: #27ae60; } .bg-promote { background: #f1c40f; color: #000; } .bg-delete { background: #e74c3c; } .bg-review { background: #34495e; }
        .fab { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; background: #2c3e50; color: #ffc107; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; box-shadow: 0 10px 20px rgba(0,0,0,0.2); text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <div style="font-size: 24px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
        <div style="font-size: 11px; color: var(--gold); margin-top: 5px;">OPERATOR: {{ session.get('op_name', 'SYSTEM') }}</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall()
    
    reg_stats = {r: 0 for r in GHANA_REGIONS}
    for r in GHANA_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE region = %s AND surname IS NOT NULL", (r,))
        reg_stats[r] = cur.fetchone()[0]
    
    guild_stats = {g: 0 for g in PBE_GUILDS}
    for g in PBE_GUILDS:
        cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE department = %s AND surname IS NOT NULL", (g,))
        guild_stats[g] = cur.fetchone()[0]
    cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="search-container">
            <input type="text" class="search-bar" placeholder="Search Master Registry...">
            <button class="btn-suite bg-review" style="padding:15px; font-size:12px;">☁️ CLOUDINARY</button>
            <div style="font-weight:bold; color:green; background:white; padding:12px; border-radius:8px; border:1px solid #ddd;">SMS: OFFLINE</div>
        </div>

        <div class="metric-card">
            <div class="metric-title">🔵 16-REGION GLOBAL METRIC</div>
            <div class="metric-grid">
                {% for reg, count in reg_stats.items() %}
                <div class="metric-item"><span>{{reg}}:</span> <b style="color:#e74c3c;">{{count}}</b></div>
                {% endfor %}
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-title">🛠️ TECHNICAL GUILDS WORKFORCE METRIC</div>
            <div class="metric-grid">
                {% for guild, count in guild_stats.items() %}
                <div class="metric-item"><span>{{guild}}</span> <b style="color:#e74c3c;">{{count}}</b></div>
                {% endfor %}
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-title">👤 PERSONNEL REGISTRY CONTROL</div>
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
                                <a href="{{ url_for('visual_editor', uid=w[6]) }}" class="btn-suite bg-print">PRINT</a>
                                <a href="#" class="btn-suite bg-review">REVIEW DOSSIER</a>
                                <a href="#" class="btn-suite bg-wa">WA</a>
                                <a href="#" class="btn-suite bg-promote">PROMOTE</a>
                                <a href="#" class="btn-suite bg-delete">DELETE</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        <a href="/admin/invite" class="fab">＋</a>
    """), reg_stats=reg_stats, guild_stats=guild_stats, workers=workers)

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['role'], session['op_name'] = 'ADMIN', request.form.get('op_name', 'ADMIN').upper()
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div style="text-align:center; padding:100px;"><h3>HQ SYSTEM LOCK</h3><form method="POST"><input name="op_name" placeholder="Operator Name" required><br><input type="password" name="password" placeholder="Key" required><br><button class="btn-suite bg-review" style="width:200px; padding:15px;">UNLOCK</button></form></div>'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
