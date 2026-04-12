import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, time, json, base64
from urllib.parse import quote
from flask import Flask, request, jsonify, render_template_string, render_template, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
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
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pbe_registry_2026' AND column_name='gender';")
    is_updated = cur.fetchone()
    if not is_updated:
        cur.execute("DROP TABLE IF EXISTS pbe_registry_2026 CASCADE;")
        cur.execute("DROP TABLE IF EXISTS pbe_audit_2026 CASCADE;")
        cur.execute("DROP TABLE IF EXISTS pbe_ip_blacklist CASCADE;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_registry_2026 (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            gender TEXT, nationality TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT, email TEXT, ghana_card_no TEXT, photo_url TEXT, ghana_card_url TEXT,
            status TEXT DEFAULT 'PENDING', otp_code TEXT, region TEXT, station TEXT,
            issuance_date DATE, expiry_date DATE
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_audit_2026 (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, actor TEXT, details TEXT, ip_address TEXT, device_info TEXT);")
    cur.execute("CREATE TABLE IF NOT EXISTS pbe_ip_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, locked_until TIMESTAMP);")
    conn.commit(); cur.close(); conn.close()

with app.app_context(): init_db()

def log_soul_action(action, details):
    role, op_name = session.get('role', 'SYSTEM'), session.get('op_name', 'Unknown')
    actor = f"{role} ({op_name})"
    remote = request.remote_addr or '127.0.0.1'
    ip = request.headers.get('X-Forwarded-For', remote).split(',')[0].strip()
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_audit_2026 (action, actor, details, ip_address) VALUES (%s, %s, %s, %s)", (action, actor, details, ip))
    conn.commit(); cur.close(); conn.close()

# --- 2. THE VISUAL EDITOR ENGINE ---
@app.route("/admin/visual-editor/<uid>")
def visual_editor(uid):
    if not session.get('role'): return redirect(url_for('admin_login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if not w: abort(404)
    return render_template('editor.html', uid=uid, w=w)

@app.route("/process-visual-print", methods=['POST'])
def process_visual_print():
    if not session.get('role'): abort(403)
    data = request.json
    img_data, uid = data.get('image').split(',')[1], data.get('uid')
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

# --- 3. UI TEMPLATES & DASHBOARD ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Supreme Command Center</title>
    <style>
        :root { --navy: #343a40; --gold: #ffc107; --bg: #f4f6f9; --text: #495057; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); margin: 0; color: var(--text); padding-bottom: 100px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 4px solid var(--gold); }
        .container { max-width: 1300px; margin: auto; padding: 15px; }
        .section-card { background: #fff; border-radius: 15px; padding: 20px; margin-bottom: 20px; border: 1px solid #e9ecef; }
        .section-title { font-size: 13px; font-weight: 800; color: #6c757d; text-transform: uppercase; margin-bottom: 15px; border-left: 4px solid var(--navy); padding-left: 10px; }
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
        .matrix-item { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 11px; font-weight: bold; color: var(--navy); }
        .registry-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .registry-table th { text-align: left; padding: 12px; border-bottom: 2px solid #dee2e6; }
        .registry-table td { padding: 15px 12px; border-bottom: 1px solid #f1f3f5; }
        .btn-cmd { padding: 8px 12px; border-radius: 6px; color: white; text-decoration: none; font-size: 10px; font-weight: bold; margin: 2px; display: inline-block; border: none; cursor: pointer; }
        .bg-blue { background: #007bff; } .bg-wa { background: #28a745; } .bg-red { background: #dc3545; } .bg-sus { background: #6c757d; } .bg-gold { background: var(--gold); color: #000; } .bg-navy { background: var(--navy); }
    </style>
</head>
<body>
    <div class="header">
        <div style="font-size: 22px; font-weight: 900; letter-spacing: 2px;">PBE COMMAND CENTER</div>
        <div style="font-size: 12px; margin-top: 5px; color: var(--gold);">OPERATOR: {{ session.get('op_name', 'SYSTEM') }}</div>
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
    reg_stats = {r: 0 for r in ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]}
    for r in reg_stats.keys():
        cur.execute("SELECT COUNT(*) FROM pbe_registry_2026 WHERE region = %s AND surname IS NOT NULL", (r,))
        reg_stats[r] = cur.fetchone()[0]
    cur.close(); conn.close()
    
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="section-card">
            <div class="section-title">🌍 REGIONAL METRIC</div>
            <div class="matrix-grid">
                {% for reg, count in reg_stats.items() %}
                <div class="matrix-item">{{reg}}: <b style="color:red; float:right;">{{count}}</b></div>
                {% endfor %}
            </div>
        </div>
        <div class="section-card">
            <div class="section-title">👥 PERSONNEL REGISTRY CONTROL</div>
            <table class="registry-table">
                <thead><tr><th>PBE-ID</th><th>NAME</th><th>RANK</th><th>COMMAND SUITE</th></tr></thead>
                <tbody>
                    {% for w in workers %}
                    <tr>
                        <td><b>{{ w[6] }}</b></td>
                        <td>{{ w[1] }}, {{ w[2] }}</td>
                        <td><b style="color:red;">{{ w[8] }}</b></td>
                        <td>
                            <a href="{{ url_for('visual_editor', uid=w[6]) }}" class="btn-cmd bg-blue">PRINT</a>
                            <a href="{{ url_for('review_cmd', uid=w[6]) }}" class="btn-cmd bg-navy">REVIEW DOSSIER</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    """), workers=workers, reg_stats=reg_stats)

@app.route("/admin/review/<uid>")
def review_cmd(uid):
    if not session.get('role'): abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("SELECT * FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    DOSSIER_HTML = """
    <div class="section-card" style="max-width:800px; margin:auto; text-align:center;">
        <h3>📋 PERSONNEL DOSSIER: {{ w[1] }} {{ w[2] }}</h3>
        <img src="{{ w[13] }}" style="width:200px; border-radius:10px; margin-bottom:20px;">
        <div style="display:flex; gap:10px; justify-content:center; flex-wrap:wrap;">
            <a href="{{ url_for('approve_cmd', uid=w[6]) }}" class="btn-cmd bg-wa">APPROVE</a>
            <a href="{{ url_for('renew_cmd', uid=w[6]) }}" class="btn-cmd bg-gold">🔄 RENEW ID</a>
            {% if session.get('role') == 'ADMIN' %}
            <a href="{{ url_for('promote_cmd', uid=w[6]) }}" class="btn-cmd bg-blue">PROMOTE</a>
            <a href="{{ url_for('delete_cmd', uid=w[6]) }}" class="btn-cmd bg-red">DELETE</a>
            {% endif %}
            <a href="/admin-dashboard" class="btn-cmd bg-sus">BACK</a>
        </div>
    </div>
    """
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", DOSSIER_HTML), w=w)

# --- 4. COMMAND LOGIC ---
@app.route("/admin/approve/<uid>")
def approve_cmd(uid):
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET status = 'ACTIVE' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

@app.route("/admin/renew/<uid>")
def renew_cmd(uid):
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET expiry_date = expiry_date + INTERVAL '2 years' WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

@app.route("/admin/promote/<uid>", methods=['GET', 'POST'])
def promote_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    if request.method == 'POST':
        conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE pbe_registry_2026 SET rank = %s WHERE pbe_uid = %s", (request.form.get('new_rank'), uid))
        conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<form method="POST"><select name="new_rank">{% for r in ranks %}<option value="{{r}}">{{r}}</option>{% endfor %}</select><button class="btn-cmd bg-navy">UPDATE</button></form>'), ranks=["Supreme Commander / CEO", "General Manager", "Chief Engineer", "Field Technician"])

@app.route("/admin/delete/<uid>")
def delete_cmd(uid):
    if session.get('role') != 'ADMIN': abort(403)
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_registry_2026 WHERE pbe_uid = %s", (uid,))
    conn.commit(); cur.close(); conn.close(); return redirect(url_for('admin_dashboard'))

# --- 5. SECURITY ---
@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD:
            session['role'], session['op_name'] = 'ADMIN', request.form.get('op_name', 'ADMIN').upper()
            return redirect(url_for('admin_dashboard'))
    LOGIN_HTML = """
    <div style="background:#1a1a1a; color:white; font-family:sans-serif; height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center;">
        <h1 style="margin-bottom:20px; letter-spacing:2px;">PBE COMMAND CENTER</h1>
        <form method="POST" style="display:flex; flex-direction:column; gap:12px; width:320px;">
            <input name="op_name" placeholder="Operator Name" style="padding:15px; border-radius:8px; border:none; background:#222; color:white;" required>
            <input type="password" name="password" placeholder="Master Access Key" style="padding:15px; border-radius:8px; border:none; background:#222; color:white;" required>
            <button style="padding:15px; border-radius:8px; border:none; background:#ffc107; font-weight:bold; cursor:pointer;">UNLOCK</button>
        </form>
    </div>
    """
    return render_template_string(LOGIN_HTML)

@app.route("/")
def index(): return redirect(url_for('admin_login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
